"""CFO view — "Is the investment case holding, and is the debt safe?" Plant × month grain; GWh and ₹ lakh/crore.

Compares against the frozen baseline (P50/P90) and the loan covenants. Inverter-level detail is omitted by rule;
causes return as escalations by materiality, recurrence or covenant watch (docs/02 §10).
"""

from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import Connection, text

from app.api.views import queries as q
from app.api.views.common import Period, card, fmt_energy, fmt_inr, fmt_pct, lens_spec, meta, omissions
from app.contracts.loader import load_loan, load_ppa
from app.twin.loader import load_plant

LENS = "cfo"
KIND_LABEL = {
    "energy_charge": "Energy charge",
    "backdown_comp": "Backdown compensation",
    "grid_unavail_comp": "Grid-unavailability compensation",
    "excess_repricing": "Excess re-pricing",
    "shortfall_comp": "Shortfall compensation",
}
ACTION = {
    "equipment_outage": "Review spares and response times with the O&M contractor",
    "grid_unavailability": "Track counted hours against the 175.2 h PPA threshold with the offtaker",
    "curtailment": "Confirm backdown compensation (C4.4) covers the lost energy",
    "underperformance": "Commission an inspection; check module/string warranty",
}
BEARER = {
    "equipment_outage": "owner",
    "grid_unavailability": "owner (uncompensated below threshold)",
    "curtailment": "offtaker (part-compensated) / owner",
    "underperformance": "owner_investigate",
}


def _months_back(m: date, n: int = 6) -> list[date]:
    out, y, mm = [], m.year, m.month
    for _ in range(n):
        out.append(date(y, mm, 1))
        mm -= 1
        if mm == 0:
            y, mm = y - 1, 12
    return out[::-1]


def escalations(
    conn: Connection,
    ds: str,
    p: Period,
    tariff: Decimal,
    export_factor: float,
    annual_revenue: Decimal,
    materiality_fraction: Decimal,
    dscr_ytd,
    lockup: Decimal,
) -> dict:
    evs = q.events(conn, ds)
    evs = evs[evs["start_ts"] < p.end_utc]
    window = _months_back(p.month)
    threshold = annual_revenue * materiality_fraction
    by_cause: dict[str, dict] = {}
    for e in evs.itertuples():
        c = by_cause.setdefault(
            e.cause_code,
            {"category": e.category, "controllable": e.controllable, "months": set(), "assets": set(), "impact": {}},
        )
        c["assets"].add(e.asset_id)
        for m in window:
            mp = Period(
                m,
                pd.Timestamp(m).tz_localize("Asia/Kolkata").tz_convert("UTC"),
                (pd.Timestamp(m).tz_localize("Asia/Kolkata") + pd.offsets.MonthBegin(1)).tz_convert("UTC"),
            )
            if not (e.start_ts < mp.end_utc and (pd.isna(e.end_ts) or e.end_ts > mp.start_utc)):
                continue
            c["months"].add(m)
            kwh = q.event_gap_kwh(conn, ds, e.asset_id, e.start_ts, e.end_ts, clip=mp) * export_factor
            c["impact"][m] = c["impact"].get(m, Decimal("0")) + Decimal(repr(kwh)) * tariff
    out, below = [], []
    for cause, c in sorted(by_cause.items()):
        annualised = (sum(c["impact"].values(), Decimal("0")) * 2).quantize(Decimal("0.01"))
        hit = sorted(c["months"])
        recurring = c["controllable"] and len(hit) >= 3
        base = {
            "cause_code": cause,
            "category": c["category"],
            "periods_hit": [m.strftime("%Y-%m") for m in hit],
            "assets_count": len(c["assets"]),
            "annualised_impact_inr": str(annualised),
            "annualised_display": fmt_inr(annualised),
        }
        if recurring:
            out.append(
                base
                | {
                    "rule": "recurrence",
                    "label": "Structural issue",
                    "bearer": "warranty_candidate",
                    "recommended_action": "Review warranty / root cause with OEM",
                    "why": f"present in {len(hit)} of the last 6 months",
                }
            )
        elif annualised >= threshold:
            out.append(
                base
                | {
                    "rule": "materiality",
                    "label": "Material loss",
                    "bearer": BEARER[c["category"]],
                    "recommended_action": ACTION[c["category"]],
                    "why": f"annualised {fmt_inr(annualised)} ≥ {fmt_inr(threshold)}",
                }
            )
        elif hit:
            below.append(base | {"why": f"annualised {fmt_inr(annualised)} < {fmt_inr(threshold)}"})
    if dscr_ytd is not None and Decimal(dscr_ytd) < lockup + Decimal("0.05"):
        out.append(
            {
                "cause_code": "DSCR",
                "rule": "covenant",
                "label": "Covenant watch",
                "periods_hit": [p.label],
                "assets_count": 0,
                "annualised_impact_inr": "0",
                "annualised_display": "—",
                "bearer": "equity",
                "recommended_action": "Prepare lender communication; review distributions",
                "why": f"DSCR YTD {dscr_ytd} < lock-up {lockup} + 0.05",
            }
        )
    return {
        "items": out,
        "below_threshold": below,
        "threshold_inr": str(threshold.quantize(Decimal("0.01"))),
        "threshold_display": fmt_inr(threshold),
        "as_of": p.label,
    }


def build(conn: Connection, info: dict, p: Period) -> dict:
    ds = info["id"]
    fin = pd.read_sql(
        text("SELECT * FROM finance_period WHERE dataset_id = :d ORDER BY period_month"), conn, params={"d": ds}
    )
    if fin.empty:
        omitted, stripped = omissions(LENS, set())
        return {
            "meta": meta(info, LENS, p),
            "decision": lens_spec(LENS)["decision"],
            "tiles": [],
            "sections": {
                "unavailable": "No PPA, baseline or loan is modelled for this measured slice; the CFO "
                "lens needs a contract and an investment case."
            },
            "events": [],
            "escalations": [],
            "omitted": omitted,
            "stripped": stripped,
        }
    plant = load_plant(info["plant_id"])
    ppa, loan = load_ppa(), load_loan()
    year = fin["period_month"].iloc[0].year
    bl = pd.read_sql(
        text(
            "SELECT * FROM baseline WHERE plant_id = :p AND status = 'approved' AND version = "
            "(SELECT max(version) FROM baseline WHERE plant_id = :p AND status = 'approved') "
            "AND valid_month >= :a AND valid_month < :b ORDER BY valid_month"
        ),
        conn,
        params={"p": info["plant_id"], "a": date(year, 1, 1), "b": date(year + 1, 1, 1)},
    )
    led = pd.read_sql(
        text(
            "SELECT period_month, accountable_kwh FROM accounting_ledger WHERE dataset_id = :d " "ORDER BY period_month"
        ),
        conn,
        params={"d": ds},
    )
    lines = pd.read_sql(text("SELECT * FROM settlement_line WHERE dataset_id = :d"), conn, params={"d": ds})
    om = q.om_line(conn, ds)

    f = fin.set_index("period_month")
    b = bl.set_index("valid_month")
    acc = led.set_index("period_month")["accountable_kwh"]
    m = p.month
    if m not in f.index:
        m = f.index[-1]
    rev, rev_b = Decimal(f.loc[m, "revenue_settled_inr"]), Decimal(b.loc[m, "revenue_p50_inr"])
    e_acc, p50, p90 = float(acc.loc[m]), float(b.loc[m, "energy_p50_kwh"]), float(b.loc[m, "energy_p90_kwh"])
    dscr_ytd = f.loc[m, "dscr_ytd"]
    provisional = bool(f.loc[m, "provisional"])
    hours = (pd.Timestamp(m) + pd.offsets.MonthBegin(1) - pd.Timestamp(m)).days * 24
    cuf = e_acc / (float(ppa.contracted_kw) * hours)
    ytd_lines = lines[(lines["period_start"] <= m)]
    recovered = sum(
        (
            Decimal(a)
            for a in ytd_lines.loc[ytd_lines["kind"].isin(["backdown_comp", "grid_unavail_comp"]), "amount_inr"]
        ),
        Decimal("0.00"),
    )
    if om is not None and not om["provisional"] and m.month == 12:
        recovered += Decimal(om["amount_inr"])
    lock = loan.lockup

    tiles = [
        card(
            "revenue_settled_inr",
            "Settled PPA revenue",
            rev,
            "INR",
            fmt_inr(rev),
            provisional=provisional,
            compare={
                "against": "revenue_baseline_inr",
                "value": str(rev_b),
                "delta_pct": round(float(rev / rev_b - 1) * 100, 2),
            },
            status_="ok" if rev >= rev_b else "warn",
            hint=f"P50 case {fmt_inr(rev_b)}",
            chip=f"accountable energy × PPA tariff ({ppa.id} C4.1) + adjustments",
        ),
        card(
            "energy_accountable_kwh",
            "Delivered energy",
            round(e_acc, 1),
            "kWh",
            fmt_energy(e_acc, "GWh"),
            compare={
                "against": "energy_baseline_p50_kwh",
                "value": str(round(p50, 1)),
                "delta_pct": round((e_acc / p50 - 1) * 100, 2),
            },
            status_="ok" if e_acc >= p50 else ("warn" if e_acc >= p90 else "alert"),
            hint=f"P50 {fmt_energy(p50, 'GWh')} · P90 {fmt_energy(p90, 'GWh')}",
        ),
        card(
            "dscr",
            "DSCR (year to date)",
            None if dscr_ytd is None else str(dscr_ytd),
            "ratio",
            "—" if dscr_ytd is None else f"{float(dscr_ytd):.2f}×",
            provisional=provisional,
            status_="alert" if dscr_ytd is not None and Decimal(dscr_ytd) < lock + Decimal("0.05") else "ok",
            hint=f"lock-up {lock}× · default {loan.default}× · sizing {loan.sizing}×",
        ),
        card(
            "cuf_actual",
            "Capacity utilisation (AC)",
            round(cuf, 4),
            "fraction",
            fmt_pct(cuf, 1),
            hint=f"declared {fmt_pct(float(ppa.declared_cuf), 1)} (annual, contracted 50 MW)",
        ),
        card(
            "recoverable_inr",
            "Recovered from counterparties (YTD)",
            recovered,
            "INR",
            fmt_inr(recovered),
            provisional=provisional,
            hint="backdown + grid compensation + O&M LDs",
        ),
        card(
            "cfads_inr",
            "CFADS (month)",
            Decimal(f.loc[m, "cfads_inr"]),
            "INR",
            fmt_inr(f.loc[m, "cfads_inr"]),
            provisional=provisional,
            hint=f"debt service {fmt_inr(f.loc[m, 'debt_service_inr'])}",
        ),
    ]
    months = list(f.index)
    sections = {
        "energy_vs_p50_p90": {
            "months": [x.strftime("%Y-%m") for x in months],
            "accountable_kwh": [round(float(acc.loc[x]), 1) for x in months],
            "p50_kwh": [float(b.loc[x, "energy_p50_kwh"]) for x in months],
            "p90_kwh": [float(b.loc[x, "energy_p90_kwh"]) for x in months],
        },
        "revenue_vs_baseline": {
            "months": [x.strftime("%Y-%m") for x in months],
            "settled_inr": [float(f.loc[x, "revenue_settled_inr"]) for x in months],
            "baseline_inr": [float(b.loc[x, "revenue_p50_inr"]) for x in months],
        },
        "dscr_vs_covenants": {
            "months": [x.strftime("%Y-%m") for x in months],
            "dscr_ytd": [None if pd.isna(f.loc[x, "dscr_ytd"]) else float(f.loc[x, "dscr_ytd"]) for x in months],
            "sizing": float(loan.sizing),
            "lockup": float(lock),
            "default": float(loan.default),
            "provisional": provisional,
        },
        "cashflow": {
            "month": m.strftime("%Y-%m"),
            "rows": [
                {"label": "Settled revenue", "display": fmt_inr(f.loc[m, "revenue_settled_inr"])},
                {"label": "O&M LDs received", "display": fmt_inr(f.loc[m, "om_ld_inr"])},
                {"label": "Opex", "display": fmt_inr(-Decimal(f.loc[m, "opex_inr"]))},
                {"label": "Tax", "display": fmt_inr(-Decimal(f.loc[m, "tax_inr"]))},
                {"label": "Maintenance capex", "display": fmt_inr(-Decimal(f.loc[m, "capex_inr"]))},
                {"label": "CFADS", "display": fmt_inr(f.loc[m, "cfads_inr"]), "total": True},
                {"label": "Debt service", "display": fmt_inr(f.loc[m, "debt_service_inr"])},
            ],
        },
        "settlement_lines": {
            "items": [
                {
                    "clause": r.clause_ref,
                    "label": KIND_LABEL[r.kind],
                    "period": r.period_kind,
                    "qty_display": fmt_energy(float(r.qty_kwh), "MWh") if r.qty_kwh is not None else "—",
                    "amount_inr": str(r.amount_inr),
                    "amount_display": fmt_inr(r.amount_inr),
                    "provisional": r.provisional,
                }
                for r in lines[
                    ((lines["period_kind"] == "month") & (lines["period_start"] == m))
                    | ((lines["period_kind"] == "year") & (m.month == 12))
                ].itertuples()
            ],
            "note": "Monthly lines are provisional until the December true-up (C4.2, C4.3, C4.5).",
        },
        "baseline": {
            "version": int(bl["version"].iloc[0]),
            "approved_by": bl["approved_by"].iloc[0],
            "approved_at": str(bl["approved_at"].iloc[0])[:10],
            "p50_annual_display": fmt_energy(float(bl["energy_p50_kwh"].sum()), "GWh"),
            "p90_annual_display": fmt_energy(float(bl["energy_p90_kwh"].sum()), "GWh"),
            "revenue_p50_display": fmt_inr(bl["revenue_p50_inr"].sum()),
            "weather_basis": bl["assumptions"].iloc[0]["weather_basis"]["radiation_db"],
            "frozen": True,
        },
    }
    esc = escalations(
        conn,
        ds,
        Period(m, p.start_utc, p.end_utc),
        ppa.tariff,
        1 - plant["loss_register"]["structural"]["export_to_delivery_point"],
        Decimal(str(bl["revenue_p50_inr"].sum())),
        Decimal(lens_spec(LENS)["materiality"]["annualised_impact_fraction_of_baseline_revenue"]),
        dscr_ytd,
        lock,
    )
    omitted, stripped = omissions(
        LENS, {"energy_lost_kwh", "peer_ratio", "loss_rate_kwh_per_h", "open_work_orders", "raw_sensor_series"}
    )
    return {
        "meta": meta(info, LENS, p, {"baseline_version": int(bl["version"].iloc[0]), "provisional": provisional}),
        "decision": lens_spec(LENS)["decision"],
        "tiles": tiles,
        "sections": sections,
        "events": [],
        "escalations": esc,
        "omitted": omitted,
        "stripped": stripped,
    }
