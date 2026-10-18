"""M3: baseline (build, approve), accounting, PPA settlement, O&M, finance."""

import re
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
import yaml
from sqlalchemy import Connection, text

from app.accounting import ledger as accounting
from app.baseline import build as baseline
from app.contracts.loader import load_loan, load_om, load_ppa, register
from app.core.bulk import audit, copy_frame, replace_rows, stable_uuid
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.money import quantize_inr
from app.core.timeutil import PLANT_TZ
from app.finance import cfads as fin
from app.ingest import weather
from app.om import availability, workorders
from app.settlement import ledger as settlement
from app.twin.loader import load_plant

PLANT_ID = "THAR1"


def baseline_yaml():
    return get_settings().configs_dir / "baseline" / "baseline_v1.yaml"


def ppa_yaml():
    return get_settings().configs_dir / "contracts" / "ppa_v1.yaml"


# ---------------------------------------------------------------- commands
def build_baseline(_args=None) -> dict:
    cfg = yaml.safe_load(baseline_yaml().read_text(encoding="utf-8"))["baseline"]
    tmy_path = weather.weather_dir() / "thar1_pvgis_tmy.json"
    if not tmy_path.exists():
        raise FileNotFoundError(f"{tmy_path} missing; run `make fetch-weather` once (needs internet)")
    tmy, inputs = weather.load_pvgis_tmy(tmy_path)
    plant = load_plant(PLANT_ID)
    loan = load_loan()
    with get_engine().begin() as conn:
        version, supersedes = baseline.next_version(conn, PLANT_ID)
        rows, summary = baseline.build_rows(tmy, inputs, plant, cfg, loan.debt_service_annual, version, supersedes)
        baseline.save_draft(conn, rows)
        audit(conn, "make baseline", "baseline.build", f"{PLANT_ID} v{version}", summary)
    if version == 1:
        _write_baseline_yaml(summary)
    print(
        f"baseline v{version} draft: P50 {summary['p50_annual'] / 1e6:.3f} GWh, P90 {summary['p90_annual'] / 1e6:.3f}"
        f" GWh, revenue P50 ₹{Decimal(summary['revenue_p50_inr']) / Decimal(1e7):.4f} cr "
        f"(radiation db {rows[0]['assumptions']['weather_basis']['radiation_db']})"
    )
    return summary


def _write_baseline_yaml(summary: dict) -> None:
    body = baseline_yaml().read_text(encoding="utf-8")
    monthly = "[" + ", ".join(f"{v:.1f}" for v in summary["p50_monthly"]) + "]"
    body = re.sub(r"p50_monthly: [^\n#]*", f"p50_monthly: {monthly}   ", body)
    body = re.sub(r"p50_annual: [^\n#]*", f"p50_annual: {summary['p50_annual']:.1f}   ", body)
    body = re.sub(r"p90_annual: [^\n#]*", f"p90_annual: {summary['p90_annual']:.1f}", body)
    body = re.sub(r"revenue_p50_inr: [^\n#]*", f'revenue_p50_inr: "{summary["revenue_p50_inr"]}"   ', body)
    baseline_yaml().write_text(body, encoding="utf-8")


def approve_baseline(_args=None, approved_by: str = "presenter") -> None:
    with get_engine().begin() as conn:
        drafts = (
            conn.execute(
                text("SELECT DISTINCT version FROM baseline WHERE plant_id = :p AND status = 'draft'"), {"p": PLANT_ID}
            )
            .scalars()
            .all()
        )
        if not drafts:
            raise baseline.BaselineError("no draft baseline to approve; run `make baseline`")
        version = max(drafts)
        baseline.approve(conn, PLANT_ID, version, approved_by)
        audit(conn, approved_by, "baseline.approve", f"{PLANT_ID} v{version}", {})
        p50 = Decimal(
            conn.execute(
                text("SELECT sum(energy_p50_kwh) FROM baseline WHERE plant_id = :p AND version = :v"),
                {"p": PLANT_ID, "v": version},
            ).scalar_one()
        )
    body = baseline_yaml().read_text(encoding="utf-8")
    if version == 1:
        body = body.replace("status: draft", "status: approved", 1)
        body = re.sub(r"approved_by: null", f"approved_by: {approved_by}", body)
        body = re.sub(r"approved_at: null", f"approved_at: {datetime.now(UTC).date().isoformat()}", body)
        baseline_yaml().write_text(body, encoding="utf-8")
        _write_declared_cuf(p50)
    print(f"baseline v{version} approved by {approved_by}; rows are now immutable")


def _write_declared_cuf(p50_annual_kwh: Decimal) -> None:
    """One-time: declared CUF = P50 / (50,000 kW × 8,760 h), rounded to 0.1 % (docs/02 §3.3)."""
    ppa = yaml.safe_load(ppa_yaml().read_text(encoding="utf-8"))["contract"]
    kw = Decimal(ppa["contracted_capacity_kw"])
    cuf = (p50_annual_kwh / (kw * 8760)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    body = ppa_yaml().read_text(encoding="utf-8")
    body = re.sub(r"declared_annual: [0-9.]+", f"declared_annual: {cuf}", body)
    ppa_yaml().write_text(body, encoding="utf-8")
    print(f"declared CUF written to ppa_v1.yaml: {cuf}")


# ---------------------------------------------------------------- pipeline steps
def step_accounting(conn: Connection, dataset_id: str) -> None:
    plant = load_plant(PLANT_ID)
    ppa = load_ppa()
    led = accounting.run(
        conn,
        dataset_id,
        PLANT_ID,
        plant["loss_register"]["structural"]["export_to_delivery_point"],
        float(ppa.contracted_kw),
        ppa.grid_window_local,
    )
    print(
        f"accounting: {len(led)} months, accountable {led['accountable_kwh'].sum() / 1e6:.3f} GWh, "
        f"max |recon delta| {led['recon_delta_pct'].abs().max():.4%}, backdown h {led['backdown_hours'].sum()}, "
        f"grid h counted {led['grid_unavail_hours_counted'].sum()}"
    )


def step_settlement(conn: Connection, dataset_id: str) -> None:
    rows = settlement.run(conn, dataset_id)
    by_kind = pd.DataFrame(rows).groupby("kind")["amount_inr"].sum()
    print("settlement:", {k: f"₹{v:,.2f}" for k, v in by_kind.items()}, f"total ₹{sum(by_kind):,.2f}")


def _frame(conn: Connection, sql: str, **params) -> pd.DataFrame:
    df = pd.read_sql(text(sql), conn, params=params)
    for c in ("ts_start", "start_ts", "end_ts", "at"):
        if c in df:
            df[c] = pd.to_datetime(df[c], utc=True)
    return df


def step_om(conn: Connection, dataset_id: str) -> None:
    om = load_om()
    register(conn, om, "om")
    expected = _frame(
        conn,
        "SELECT asset_id, ts_start, e_potential_kwh FROM expected_output WHERE dataset_id = :d "
        "AND model_version = 'perf-1.0'",
        d=dataset_id,
    )
    actual = _frame(
        conn,
        "SELECT asset_id, ts_start, e_kwh, quality::text AS quality FROM actual_output " "WHERE dataset_id = :d",
        d=dataset_id,
    )
    events = _frame(
        conn,
        "SELECT id, asset_id, category::text AS category, cause_code, start_ts, end_ts, "
        "confidence::text AS confidence FROM event WHERE dataset_id = :d ORDER BY start_ts",
        d=dataset_id,
    )
    f = availability.interval_frame(expected, actual, events, om)
    f["month"] = f["ts_start"].dt.tz_convert(PLANT_TZ).dt.to_period("M").dt.to_timestamp().dt.date
    monthly = {}
    for m, g in f.groupby("month"):
        a, loss, ep = availability.energy_based(g)
        monthly[str(m)] = {"a_e": round(a, 6), "loss_kwh": round(loss, 1), "ep_eligible_kwh": round(ep, 1)}
    year = f["month"].iloc[0].year
    a_y, loss_y, ep_y = availability.energy_based(f)
    complete = len(monthly) == 12
    ld = availability.liquidated_damages(Decimal(repr(a_y)).quantize(Decimal("0.000001")), Decimal(repr(ep_y)), om)
    ld_row = {
        "id": stable_uuid("om_ld", dataset_id, year),
        "dataset_id": dataset_id,
        "plant_id": PLANT_ID,
        "year": year,
        "availability_energy": ld.availability,
        "ld_kwh": ld.ld_kwh.quantize(Decimal("0.1")),
        "amount_inr": ld.amount,
        "capped": ld.capped,
        "contract_id": om.id,
        "inputs": ld.inputs | {"loss_outage_eligible_kwh": round(loss_y, 1), "monthly": monthly},
        "provisional": not complete,
    }
    replace_rows(conn, "om_ld_line", {"dataset_id": dataset_id}, pd.DataFrame([ld_row]))

    # work orders: loss rate = E_potential rate − actual rate at the first daylight interval of the event
    loss_rate = {}
    for e in events.itertuples():
        if "/" not in e.asset_id:
            continue
        rows = f[(f["asset_id"] == e.asset_id) & (f["ts_start"] >= e.start_ts) & (f["e_potential_kwh"] > 0)].head(1)
        if len(rows):
            r = rows.iloc[0]
            loss_rate[e.id] = max(0.0, (r["e_potential_kwh"] - (r["e_kwh"] if pd.notna(r["e_kwh"]) else 0.0)) * 4)
    oplog = _frame(conn, "SELECT asset_id, kind, at FROM operator_log WHERE dataset_id = :d", d=dataset_id)
    data_end = f["ts_start"].max() + pd.Timedelta(minutes=15)
    wos = workorders.build(events, oplog, loss_rate, data_end, om)
    for w in wos:
        w["id"] = stable_uuid("wo", dataset_id, w["event_id"])
    ids = [str(i) for i in events["id"]]
    conn.execute(text("DELETE FROM work_order WHERE event_id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids})
    if wos:
        copy_frame(
            conn,
            "work_order",
            pd.DataFrame(wos)[
                [
                    "id",
                    "event_id",
                    "severity",
                    "status",
                    "opened_at",
                    "acked_at",
                    "onsite_at",
                    "restored_at",
                    "verified_at",
                    "priority_score",
                    "priority_inputs",
                    "source_kind",
                ]
            ],
        )
    wdf = pd.DataFrame(wos)
    print(
        f"om: A_E {a_y:.4%} (guarantee {om.guarantee}), LD {ld.ld_kwh:,.0f} kWh = ₹{ld.amount:,.2f}"
        f"{' (capped)' if ld.capped else ''}; work orders {len(wos)}, SLA breaches "
        f"{workorders.sla_breaches(wdf) if len(wdf) else 0}, MTTR {workorders.mttr_h(wdf) if len(wdf) else 0:.1f} h"
    )


def step_finance(conn: Connection, dataset_id: str) -> None:
    loan = load_loan()
    register(conn, loan, "loan")
    led = accounting.read_ledger(conn, dataset_id)
    year = led["period_month"].iloc[0].year
    bl = baseline.approved_months(conn, PLANT_ID, year)
    capex_annual = Decimal(bl["assumptions"].iloc[0]["maintenance_capex_inr_annual"])
    capex = fin.split_annual(capex_annual)
    debt = fin.split_annual(loan.debt_service_annual)
    ld = conn.execute(
        text("SELECT amount_inr, provisional FROM om_ld_line WHERE dataset_id = :d AND year = :y"),
        {"d": dataset_id, "y": year},
    ).first()
    complete = len(led) == 12
    rows, cf_sum, debt_sum = [], Decimal("0"), Decimal("0")
    for month in led["period_month"]:
        revenue = settlement.total(conn, dataset_id, month)
        om_ld = Decimal(ld.amount_inr) if (ld and month.month == 12 and not ld.provisional) else Decimal("0.00")
        b = bl[bl["valid_month"] == month].iloc[0]
        cf = fin.cfads(revenue, om_ld, Decimal(b["opex_inr"]), Decimal(b["tax_inr"]), capex[month.month - 1])
        cf_sum += cf
        debt_sum += debt[month.month - 1]
        rows.append(
            {
                "dataset_id": dataset_id,
                "plant_id": PLANT_ID,
                "period_month": month,
                "revenue_settled_inr": quantize_inr(revenue),
                "om_ld_inr": om_ld,
                "opex_inr": Decimal(b["opex_inr"]),
                "tax_inr": Decimal(b["tax_inr"]),
                "capex_inr": capex[month.month - 1],
                "cfads_inr": cf,
                "debt_service_inr": debt[month.month - 1],
                "dscr_ytd": fin.dscr(cf_sum, debt_sum),
                "provisional": not complete,
            }
        )
    replace_rows(conn, "finance_period", {"dataset_id": dataset_id}, pd.DataFrame(rows))
    print(
        f"finance: CFADS ₹{cf_sum / Decimal(1e7):.4f} cr, debt ₹{debt_sum / Decimal(1e7):.4f} cr, "
        f"DSCR_YTD {rows[-1]['dscr_ytd']} (lock-up {loan.lockup}, default {loan.default})"
    )


STEPS = {"accounting": step_accounting, "settlement": step_settlement, "om": step_om, "finance": step_finance}
