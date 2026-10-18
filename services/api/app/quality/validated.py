"""Validated inverter AC energy -> actual_output (docs/02 §2.2, metric energy_actual_kwh).

E = AC_POWER(kW) × 0.25 h per interval. Missing intervals and stalled heartbeats become `no_data` (comms loss is a
data gap, not an energy loss).
"""

import pandas as pd

from app.core.timeutil import INTERVAL_H


def energy_actual(
    meas: pd.DataFrame, inverter_ids: list[str], index: pd.DatetimeIndex, dataset_id: str
) -> pd.DataFrame:
    """meas: long measurement rows (asset_id, quantity, ts_start, value, value_text, quality)."""
    frames = []
    ac = meas[meas["quantity"] == "ac_power_kw"]
    status = meas[meas["quantity"] == "status"]
    hb = meas[meas["quantity"] == "heartbeat"]
    for asset in inverter_ids:
        a = ac[ac["asset_id"] == asset].set_index("ts_start").reindex(index)
        out = pd.DataFrame(index=index)
        out["e_kwh"] = a["value"] * INTERVAL_H
        out["quality"] = a["quality"].fillna("no_data")
        s = status[status["asset_id"] == asset].set_index("ts_start").reindex(index)
        out["status"] = s["value_text"]
        h = hb[hb["asset_id"] == asset].set_index("ts_start").reindex(index)["value"]
        if h.notna().any():
            stalled = h.diff().eq(0) | h.isna()
            out.loc[stalled, "quality"] = "no_data"
        out.loc[out["quality"] == "no_data", "e_kwh"] = None
        out = out.rename_axis("ts_start").reset_index()
        out.insert(0, "asset_id", asset)
        frames.append(out)
    res = pd.concat(frames, ignore_index=True)
    res.insert(0, "dataset_id", dataset_id)
    return res[["dataset_id", "asset_id", "ts_start", "e_kwh", "quality", "status"]]
