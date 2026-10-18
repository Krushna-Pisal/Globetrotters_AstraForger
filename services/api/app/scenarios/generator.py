"""Synthetic year generator (docs/06 §5). Pure function of (scenario yaml, plant yaml, real weather, seed).

Physics on real weather first, then recorded deviations on top. Texture, soiling and the silent derate act on DC
before the inverter (D20), so clipping hides some of them exactly as it would on a real plant. Faults are reported the
way SCADA reports them: power and status codes; the silent derate has no status code; comms loss removes rows and
stalls the heartbeat while the meter keeps counting. Every injected loss is written to ground truth.
Engines never import this package (import-linter).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.core.timeutil import INTERVAL_H, PLANT_TZ
from app.performance import model

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


@dataclass
class Scenario:
    index: pd.DatetimeIndex
    inverters: list[str]  # asset names, e.g. INV-07
    ac_kw: np.ndarray  # (n_intervals, n_inverters) reported AC power (before comms-loss removal)
    status: np.ndarray  # (n_intervals, n_inverters) status codes
    reported: np.ndarray  # (n_intervals, n_inverters) bool: row exists in telemetry
    heartbeat: np.ndarray
    plant_status: np.ndarray
    setpoint_kw: np.ndarray
    meter_kwh: np.ndarray
    weather: pd.DataFrame  # 15-min weather + poa + t_cell
    operator_log: list[dict]
    ground_truth: dict
    soiling_fraction: pd.Series  # by local date
    extras: dict = field(default_factory=dict)


def _local(ts: str) -> pd.Timestamp:
    return pd.Timestamp(ts).tz_localize(PLANT_TZ).tz_convert("UTC")


def soiling_series(days: list[date], cfg: dict, daily_precip: pd.Series) -> tuple[pd.Series, list[date]]:
    """Fraction of DC lost on each local day; cleanings reset at 06:00 (before generation) unless missed."""
    rates = cfg["daily_rate_by_month"]
    clean = cfg["cleaning"]
    first = pd.Timestamp(clean["first"]).date()
    missed = {pd.Timestamp(d).date() for d in clean.get("missed", [])}
    scheduled = set()
    d = first
    while d <= days[-1]:
        scheduled.add(d)
        d += timedelta(days=clean["interval_days"])
    performed = sorted(scheduled - missed)
    rain = cfg["rain_reset"]
    s, out = 0.0, {}
    for day in days:
        if day in performed:
            s = 0.0
        out[day] = s
        s += rates[MONTHS[day.month - 1]]
        if daily_precip.get(day, 0.0) >= rain["daily_precip_mm_at_least"]:
            s *= 1.0 - rain["removes_fraction"]
    return pd.Series(out), [d for d in performed if days[0] <= d <= days[-1]]


def generate(scenario: dict, plant: dict, weather15: pd.DataFrame) -> Scenario:
    p = model.ChainParams.from_plant(plant)
    index = weather15.index
    names = [n for b in plant["hierarchy"]["blocks"] for n in b["inverters"]]
    n_t, n_i = len(index), len(names)
    tex = scenario["texture"]
    rng = np.random.default_rng(scenario["seed"])
    factors = rng.normal(1.0, tex["inverter_efficiency_spread_sigma"], n_i)
    noise = rng.normal(1.0, tex["interval_noise_sigma"], (n_t, n_i))
    meter_noise = rng.normal(1.0, tex["meter_noise_sigma"], n_t)

    chain = model.dc_chain(weather15, p, INTERVAL_H)
    p_dc_nom = chain["p_dc_kw"].to_numpy()
    local_days = index.tz_convert(PLANT_TZ).date
    days = sorted(set(local_days))
    precip = pd.Series(weather15["precip_mm"].to_numpy()).groupby(local_days).sum()
    soil_day, cleanings = soiling_series(days, scenario["soiling"], precip)
    soil = soil_day.reindex(local_days).to_numpy()

    derate = np.ones((n_t, n_i))
    silent = [e for e in scenario["events"] if e["kind"] == "silent_underperformance"]
    for e in silent:
        m = (index >= _local(e["start"])) & (index < _local(e["end"]))
        derate[m, names.index(e["asset"])] *= 1.0 - e["derate_fraction"]

    base_dc = p_dc_nom[:, None] * factors[None, :] * noise
    ac_clean = model.ac_from_dc(base_dc, p)
    ac_soiled = model.ac_from_dc(base_dc * (1 - soil)[:, None], p)
    ac = model.ac_from_dc(base_dc * (1 - soil)[:, None] * derate, p)

    status = np.full((n_t, n_i), "RUNNING", dtype=object)
    plant_status = np.full(n_t, "RUNNING", dtype=object)
    setpoint = np.full(n_t, float(plant["capacity"]["contracted_ac_kw"]))
    reported = np.ones((n_t, n_i), dtype=bool)
    dp = 1.0 - p.export_loss
    truth_events, oplog = [], []

    for e in silent:
        lost = (ac_soiled - ac)[:, names.index(e["asset"])].sum() * INTERVAL_H * dp
        truth_events.append(_truth(e, e["asset"], _local(e["start"]), _local(e["end"]), lost))

    for e in scenario["events"]:
        kind = e["kind"]
        if kind == "equipment_outage":
            start, end = _local(e["start"]), _local(e["end"])
            m = (index >= start) & (index < end)
            j = names.index(e["asset"])
            lost = ac[m, j].sum() * INTERVAL_H * dp
            ac[m, j] = 0.0
            status[m, j] = e["status"]
            truth_events.append(_truth(e, e["asset"], start, end, lost))
            for k, at in (
                ("acknowledged", start + pd.Timedelta(hours=0.5)),
                ("onsite", start + pd.Timedelta(hours=3)),
                ("restored", end),
            ):
                oplog.append({"asset": e["asset"], "kind": k, "at": at, "note": f"{e['cause_code']} work order"})
        elif kind == "grid_unavailability":
            start, end = _local(e["start"]), _local(e["end"])
            m = (index >= start) & (index < end)
            lost = ac[m].sum() * INTERVAL_H * dp
            ac[m] = 0.0
            status[m] = "WAIT_GRID"
            plant_status[m] = e["status"]
            truth_events.append(_truth(e, "THAR1", start, end, lost))
        elif kind == "curtailment":
            d0, d1 = pd.Timestamp(e["start_date"]).date(), pd.Timestamp(e["end_date"]).date()
            lost_total, windows = 0.0, []
            d = d0
            while d <= d1:
                ws, we = (_local(f"{d} {e['daily_window'][0]}"), _local(f"{d} {e['daily_window'][1]}"))
                m = (index >= ws) & (index < we)
                total = ac[m].sum(axis=1)
                scale = np.where(total > e["setpoint_kw"], e["setpoint_kw"] / np.maximum(total, 1e-9), 1.0)
                before = ac[m].sum()
                ac[m] = ac[m] * scale[:, None]
                lost_total += (before - ac[m].sum()) * INTERVAL_H * dp
                status[m] = "CURTAILED"
                plant_status[m] = e["status"]
                setpoint[m] = e["setpoint_kw"]
                windows.append([str(ws), str(we)])
                d += timedelta(days=1)
            t = _truth(e, "THAR1", _local(f"{d0} 00:00"), _local(f"{d1 + timedelta(days=1)} 00:00"), lost_total)
            t["windows_utc"] = windows
            t["backdown_hours"] = (
                len(windows)
                * (
                    pd.Timedelta(e["daily_window"][1] + ":00") - pd.Timedelta(e["daily_window"][0] + ":00")
                ).total_seconds()
                / 3600
            )
            truth_events.append(t)
        elif kind == "comms_loss":
            start, end = _local(e["start"]), _local(e["end"])
            m = (index >= start) & (index < end)
            reported[m, names.index(e["asset"])] = False
            truth_events.append(_truth(e, e["asset"], start, end, 0.0))

    heartbeat = np.cumsum(reported, axis=0).astype(float)  # stalls while not reporting
    meter = ac.sum(axis=1) * INTERVAL_H * dp * meter_noise

    for d in cleanings:
        oplog.append({"asset": "THAR1", "kind": "cleaning", "at": _local(f"{d} 06:00"), "note": "module cleaning"})

    soil_lost = (ac_clean - ac_soiled).sum(axis=1) * INTERVAL_H * dp
    soil_daily = pd.Series(soil_lost).groupby(local_days).sum()
    weather = weather15.copy()
    weather["poa"] = chain["poa"].to_numpy()
    weather["t_cell"] = chain["t_cell"].to_numpy()
    truth = {
        "dataset_id": scenario["dataset_id"],
        "seed": scenario["seed"],
        "texture": tex,
        "inverter_factors": dict(zip(names, np.round(factors, 6).tolist(), strict=True)),
        "events": truth_events,
        "soiling_daily": [
            {
                "date": str(d),
                "true_soiling_fraction": round(float(soil_day[d]), 6),
                "true_lost_kwh_delivery_point": round(float(soil_daily.get(d, 0.0)), 3),
            }
            for d in days
        ],
        "cleanings_performed": [str(d) for d in cleanings],
        "note": "Synthetic scenario ground truth. Read only by tests and the scorecard, never by engines.",
    }
    return Scenario(
        index, names, ac, status, reported, heartbeat, plant_status, setpoint, meter, weather, oplog, truth, soil_day
    )


def _truth(e: dict, asset: str, start: pd.Timestamp, end: pd.Timestamp, lost: float) -> dict:
    return {
        "id": e["id"],
        "asset": asset,
        "kind": e["kind"],
        "cause_code": e["cause_code"],
        "start_utc": str(start),
        "end_utc": str(end),
        "true_lost_kwh_delivery_point": round(float(lost), 3),
    }
