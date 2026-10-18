"""Engineer view — "Is the plant physically healthy, and which component is underperforming?"

Compares against weather-adjusted expected output only (never the baseline or money). Units: kWh.
"""

import pandas as pd
from sqlalchemy import Connection

from app.api.views import queries as q
from app.api.views.common import (
    Period,
    asset_names,
    cached,
    card,
    fmt_energy,
    fmt_pct,
    fmt_ts,
    lens_spec,
    meta,
    omissions,
)
from app.detection import peer
from app.performance import kpi
from app.quality import score
from app.twin.loader import load_plant

LENS = "engineer"
CATEGORY_ORDER = ["equipment_outage", "grid_unavailability", "curtailment", "underperformance"]
CATEGORY_LABEL = {
    "equipment_outage": "Outages (availability)",
    "grid_unavailability": "Grid unavailability",
    "curtailment": "Curtailment",
    "underperformance": "Underperformance (suspected)",
}
CATEGORY_SHORT = {
    "equipment_outage": "Outages",
    "grid_unavailability": "Grid",
    "curtailment": "Curtailment",
    "underperformance": "Underperf.",
}


def build(conn: Connection, info: dict, p: Period) -> dict:
    plant = load_plant(info["plant_id"])
    names = asset_names(conn, info["plant_id"])
    ds = info["id"]
    daily = q.daily_energy(conn, ds, p)
    ep, ea = float(daily["ep"].sum()), float(daily["ea"].sum())
    band = float(daily["band"].max()) if len(daily) else 0.0
    gap = ep - ea
    model_note = (
        "pvlib chain on site weather"
        if info["kind"] == "synthetic"
        else "per-inverter fit on the plant irradiance sensor (real-data mode)"
    )
    act = q.month_actual(conn, ds, p)
    poa = q.month_poa(conn, ds, p)
    ws_irr, ws_ok = q.ws_quality(conn, ds, p)
    dq = score.daily_score(pd.DatetimeIndex(sorted(act["ts_start"].unique())), ws_irr, ws_ok, act) if len(act) else None
    dq_mean = float(dq["score"].mean()) if dq is not None and len(dq) else None

    om = q.om_line(conn, ds)
    a_e = om["inputs"]["monthly"].get(p.month.isoformat(), {}).get("a_e") if om else None

    tiles = [
        card(
            "energy_potential_kwh",
            "Expected energy",
            round(ep, 1),
            "kWh",
            fmt_energy(ep, "kWh"),
            source_kind="modeled",
            hint=f"pvlib model, ±{band * 100:.1f} % band (95 %)",
        ),
        card(
            "energy_actual_kwh",
            "Actual inverter energy",
            round(ea, 1),
            "kWh",
            fmt_energy(ea, "kWh"),
            source_kind="synthetic_scenario" if info["kind"] == "synthetic" else "measured",
            compare={"against": "energy_potential_kwh", "delta_pct": round((ea / ep - 1) * 100, 2) if ep else None},
        ),
        card(
            "energy_lost_kwh",
            "Gap to expected",
            round(gap, 1),
            "kWh",
            fmt_energy(gap, "kWh"),
            status_="warn" if ep and gap / ep > band else "ok",
            hint=f"{fmt_pct(gap / ep if ep else None)} of expected",
        ),
    ]
    if a_e is not None:
        tiles.append(
            card(
                "availability_energy",
                "Energy availability",
                a_e,
                "fraction",
                fmt_pct(a_e, 2),
                status_="ok" if a_e >= 0.99 else "alert",
                provisional=True,
                hint="O&M basis, month",
            )
        )
    if dq_mean is not None:
        tiles.append(
            card(
                "data_quality_score",
                "Data quality",
                round(dq_mean, 4),
                "fraction",
                fmt_pct(dq_mean, 1),
                status_="ok" if dq_mean >= 0.98 else "warn",
                hint="ok intervals ÷ expected daylight",
            )
        )

    sections: dict = {
        "daily_energy": {
            "model_note": model_note,
            "days": [str(d) for d in daily["d"]],
            "expected_kwh": daily["ep"].round(1).tolist(),
            "actual_kwh": daily["ea"].round(1).fillna(0).tolist(),
            "band_low_kwh": (daily["ep"] * (1 - daily["band"])).round(1).tolist(),
            "band_high_kwh": (daily["ep"] * (1 + daily["band"])).round(1).tolist(),
            "band_span_kwh": (daily["ep"] * 2 * daily["band"]).round(1).tolist(),
        }
    }

    dc = plant.get("inverter", {}).get("dc_kwp_each")
    if dc:
        pr = cached(
            ("pr", ds),
            lambda: kpi.monthly_pr(conn, ds, dc * plant["inverter"]["count"], plant["module"]["gamma_pdc_per_c"]),
        )
        cur = pr[pr["month"] == p.month]
        sections["pr_trend"] = {
            "months": [m.strftime("%Y-%m") for m in pr["month"]],
            "pr": pr["pr"].round(4).tolist(),
            "pr_25": pr["pr_25"].round(4).tolist(),
            "expected_pr_25": pr["pr_25_expected"].round(4).tolist(),
            "band_low": pr["pr_25_low"].round(4).tolist(),
            "band_high": pr["pr_25_high"].round(4).tolist(),
            "band_span": (pr["pr_25_high"] - pr["pr_25_low"]).round(4).tolist(),
        }
        if len(cur):
            pi = float(cur["performance_index"].iloc[0])
            tiles.insert(
                3,
                card(
                    "pr_25",
                    "PR (25 °C corrected)",
                    round(float(cur["pr_25"].iloc[0]), 4),
                    "fraction",
                    fmt_pct(float(cur["pr_25"].iloc[0]), 1),
                    status_="ok" if pi >= 0.98 else "warn",
                    hint=f"expected {fmt_pct(float(cur['pr_25_expected'].iloc[0]))} · index {pi:.3f}",
                ),
            )
    else:
        sections["pr_trend"] = {"unavailable": "No DC nameplate published for this plant; PR needs P_STC."}

    normal = act["status"].isna() | act["status"].isin(["RUNNING", "WAIT_GRID"])
    ratios = peer.daily_peer_ratio(act[normal], poa > 0) if len(act) else pd.DataFrame()
    assets = sorted(ratios.columns, key=lambda a: names.get(a, a))
    sections["inverter_heatmap"] = {
        "metric_id": "peer_ratio",
        "assets": [names.get(a, a) for a in assets],
        "days": [str(d) for d in ratios.index],
        "ratio": [[None if pd.isna(v) else round(float(v), 4) for v in ratios[a]] for a in assets],
        "threshold": peer.THRESHOLD,
    }

    evs = q.events(conn, ds, p)
    rows, by_cat = [], {c: 0.0 for c in CATEGORY_ORDER}
    for e in evs.itertuples():
        total = q.event_gap_kwh(conn, ds, e.asset_id, e.start_ts, e.end_ts)
        in_month = q.event_gap_kwh(conn, ds, e.asset_id, e.start_ts, e.end_ts, clip=p)
        by_cat[e.category] = by_cat.get(e.category, 0.0) + in_month
        end = e.end_ts if pd.notna(e.end_ts) else None
        rows.append(
            {
                "id": e.id,
                "asset": names.get(e.asset_id, e.asset_id),
                "asset_id": e.asset_id,
                "category": e.category,
                "cause_code": e.cause_code,
                "start": fmt_ts(e.start_ts),
                "end": fmt_ts(end),
                "duration_h": round((end - e.start_ts).total_seconds() / 3600, 1) if end is not None else None,
                "lost_kwh": round(total, 1),
                "lost_display": fmt_energy(total, "kWh"),
                "confidence": e.confidence,
                "evidence": {
                    "rules": e.evidence.get("rules", []),
                    "detail": {k: v for k, v in e.evidence.get("metrics", {}).items() if k != "scope"},
                },
                "status": "ongoing" if end is None else "closed",
                "wording": "symptom detected — inspect" if e.confidence == "suspected" else "fault reported by SCADA",
            }
        )
    steps = [{"order": 1, "bucket": "expected", "label": "Expected", "short": "Expected", "value_kwh": round(ep, 1)}]
    rem = ep
    for i, c in enumerate(CATEGORY_ORDER, start=2):
        steps.append(
            {
                "order": i,
                "bucket": c,
                "label": CATEGORY_LABEL[c],
                "short": CATEGORY_SHORT[c],
                "value_kwh": round(-by_cat.get(c, 0.0), 1),
            }
        )
        rem -= by_cat.get(c, 0.0)
    steps.append(
        {
            "order": 6,
            "bucket": "not_yet_attributed",
            "label": "Soiling + residual (not yet split)",
            "short": "Soiling + other",
            "value_kwh": round(ea - rem, 1),
        }
    )
    steps.append({"order": 7, "bucket": "actual", "label": "Actual", "short": "Actual", "value_kwh": round(ea, 1)})
    running = 0.0
    for i, st in enumerate(steps):
        v = st["value_kwh"]
        if i in (0, len(steps) - 1):
            st |= {"kind": "total", "base_kwh": 0.0, "bar_kwh": v}
            running = v
        else:
            nxt = running + v
            st |= {"kind": "step", "base_kwh": round(min(running, nxt), 1), "bar_kwh": round(abs(v), 1)}
            running = nxt
    sections["loss_waterfall_kwh"] = {
        "steps": steps,
        "closes": True,
        "precedence": ["outage", "grid", "curtailment", "underperformance"],
        "note": "Preliminary: gaps inside detected event windows. The attribution engine (M4) splits soiling, "
        "variance vs assumed losses and the explicit residual.",
    }
    present = (
        {
            "revenue_settled_inr",
            "revenue_bridge_inr",
            "recoverable_inr",
            "dscr",
            "cfads_inr",
            "energy_baseline_p50_kwh",
            "tariff",
        }
        if info["kind"] == "synthetic"
        else {"tariff"}
    )
    omitted, stripped = omissions(LENS, present)
    return {
        "meta": meta(info, LENS, p, {"data_quality_score": dq_mean}),
        "decision": lens_spec(LENS)["decision"],
        "tiles": tiles,
        "sections": sections,
        "events": rows,
        "omitted": omitted,
        "stripped": stripped,
    }
