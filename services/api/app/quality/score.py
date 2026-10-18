"""Daily data-quality score (docs/02 §2.3, metric data_quality_score).

score(day) = ok intervals / expected daylight intervals, across inverters + the weather station.
Daylight (D18) = the weather station's irradiance > 0, or any inverter producing when the station is missing.
"""

import pandas as pd

from app.core.timeutil import local_date


def daylight_mask(index: pd.DatetimeIndex, ws_irr: pd.Series, actual: pd.DataFrame) -> pd.Series:
    irr = ws_irr.reindex(index)
    producing = actual.groupby("ts_start")["e_kwh"].max().reindex(index).fillna(0) > 0
    return (irr > 0) | (irr.isna() & producing)


def daily_score(index: pd.DatetimeIndex, ws_irr: pd.Series, ws_ok: pd.Series, actual: pd.DataFrame) -> pd.DataFrame:
    """ws_irr/ws_ok indexed by ts_start; actual = actual_output frame. Returns date, score, ok, expected."""
    day = daylight_mask(index, ws_irr, actual)
    n_inv = actual["asset_id"].nunique()
    inv_ok = actual[actual["quality"] == "ok"].groupby("ts_start").size().reindex(index).fillna(0)
    ws_ok = ws_ok.reindex(index).astype("boolean").fillna(False).astype(int)
    frame = pd.DataFrame({"daylight": day, "ok": inv_ok + ws_ok}, index=index)
    frame = frame[frame["daylight"]]
    frame["date"] = local_date(frame.index).to_numpy()
    agg = frame.groupby("date").agg(ok=("ok", "sum"), n=("ok", "size"))
    agg["expected"] = agg["n"] * (n_inv + 1)
    agg["score"] = agg["ok"] / agg["expected"]
    return agg[["ok", "expected", "score"]].reset_index()
