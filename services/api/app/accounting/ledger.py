"""Delivery-point ledger (docs/02 §5, D11). Accountable energy = MTR-DP export; the hour counts settlement needs.

Per local month:
- meter_kwh: Σ delivery-meter intervals; a `no_data` meter interval is estimated as Σ inverter actual × (1 − 0.015)
- inverter_sum_kwh, export_loss_kwh = inverter_sum × 0.015, recon_delta_pct = (meter − inv × 0.985) / meter
- hours_with_generation: local clock hours with accountable export > 0
- backdown_hours: intervals with an SLDC setpoint below contracted capacity × 0.25 h
- grid_unavail_hours_counted: plant OFFLINE intervals inside the PPA window (08:00–18:00 local) × 0.25 h
Reads stored rows only; imports nothing but app.core (settlement firewall).
"""

import pandas as pd
from sqlalchemy import Connection, text

from app.core.bulk import replace_rows
from app.core.timeutil import INTERVAL_H, PLANT_TZ

RECON_TOLERANCE = 0.01


def _read(conn: Connection, sql: str, **params) -> pd.DataFrame:
    df = pd.read_sql(text(sql), conn, params=params)
    if "ts_start" in df:
        df["ts_start"] = pd.to_datetime(df["ts_start"], utc=True)
    return df


def compute(
    conn: Connection,
    dataset_id: str,
    plant_id: str,
    export_loss: float,
    contracted_kw: float,
    grid_window: tuple[str, str],
) -> pd.DataFrame:
    meter = _read(
        conn,
        "SELECT m.ts_start, m.value, m.quality::text AS quality FROM measurement m "
        "JOIN asset a ON a.id = m.asset_id WHERE m.dataset_id = :d AND a.plant_id = :p "
        "AND a.kind = 'meter' AND m.quantity = 'energy_export_kwh'",
        d=dataset_id,
        p=plant_id,
    )
    if meter.empty:
        return pd.DataFrame()
    inv = _read(
        conn,
        "SELECT ts_start, sum(e_kwh) AS e_kwh FROM actual_output WHERE dataset_id = :d " "GROUP BY ts_start",
        d=dataset_id,
    )
    plant = _read(
        conn,
        "SELECT ts_start, quantity, value, value_text FROM measurement WHERE dataset_id = :d "
        "AND asset_id = :p AND quantity IN ('status', 'setpoint_kw')",
        d=dataset_id,
        p=plant_id,
    )
    idx = pd.DatetimeIndex(sorted(set(meter["ts_start"]) | set(inv["ts_start"])))
    f = pd.DataFrame(index=idx)
    m = meter.set_index("ts_start")
    f["meter_raw"] = m["value"].where(m["quality"] != "no_data")
    f["inv"] = inv.set_index("ts_start")["e_kwh"].reindex(idx).fillna(0.0)
    f["estimated"] = f["meter_raw"].isna()
    f["meter"] = f["meter_raw"].fillna(f["inv"] * (1 - export_loss))
    st = plant[plant["quantity"] == "status"].set_index("ts_start")["value_text"].reindex(idx)
    sp = plant[plant["quantity"] == "setpoint_kw"].set_index("ts_start")["value"].reindex(idx)
    local = idx.tz_convert(PLANT_TZ)
    f["month"] = local.to_period("M").to_timestamp().date
    f["hour"] = local.floor("h")
    f["backdown"] = (sp < contracted_kw).fillna(False).to_numpy()
    w0, w1 = (pd.Timestamp(t).time() for t in grid_window)
    in_window = (local.time >= w0) & (local.time < w1)
    f["grid"] = ((st == "OFFLINE").fillna(False).to_numpy()) & in_window

    rows = []
    for month, g in f.groupby("month"):
        hourly = g.groupby("hour")["meter"].sum()
        meter_kwh = float(g["meter"].sum())
        inv_kwh = float(g["inv"].sum())
        rows.append(
            {
                "dataset_id": dataset_id,
                "plant_id": plant_id,
                "period_month": month,
                "meter_kwh": meter_kwh,
                "inverter_sum_kwh": inv_kwh,
                "export_loss_kwh": inv_kwh * export_loss,
                "accountable_kwh": meter_kwh,
                "recon_delta_pct": (meter_kwh - inv_kwh * (1 - export_loss)) / meter_kwh if meter_kwh else 0.0,
                "rule_refs": {
                    "accountable": "02 §5.1 delivery-point meter MTR-DP (C4.6)",
                    "estimated_meter_intervals": int(g["estimated"].sum()),
                    "estimation_rule": "sum inverter actual x (1 - export_loss)",
                    "recon_tolerance": RECON_TOLERANCE,
                    "grid_window_local": list(grid_window),
                },
                "hours_with_generation": float((hourly > 0).sum()),
                "backdown_hours": float(g["backdown"].sum() * INTERVAL_H),
                "grid_unavail_hours_counted": float(g["grid"].sum() * INTERVAL_H),
            }
        )
    return pd.DataFrame(rows)


def run(
    conn: Connection,
    dataset_id: str,
    plant_id: str,
    export_loss: float,
    contracted_kw: float,
    grid_window: tuple[str, str],
) -> pd.DataFrame:
    ledger = compute(conn, dataset_id, plant_id, export_loss, contracted_kw, grid_window)
    replace_rows(conn, "accounting_ledger", {"dataset_id": dataset_id}, ledger)
    return ledger


def read_ledger(conn: Connection, dataset_id: str) -> pd.DataFrame:
    return pd.read_sql(
        text("SELECT * FROM accounting_ledger WHERE dataset_id = :d ORDER BY period_month"),
        conn,
        params={"d": dataset_id},
    )
