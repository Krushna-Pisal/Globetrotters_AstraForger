"""Status-code rule (docs/02 §8.1 rule 1): runs of non-normal SCADA status per asset -> events.

The mapping from status code to category/cause comes from the plant's status dictionary (configs/plant, D17).
Inverter FAULT_*/OFFLINE -> equipment_outage (confirmed); plant OFFLINE -> grid_unavailability; plant CURTAILED ->
curtailment with the setpoint register as evidence.
"""

import pandas as pd

from app.core.timeutil import INTERVAL


def runs(status: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    """status: indexed by ts_start (sorted). Returns (start, end_exclusive, code) for each contiguous run."""
    s = status.dropna()
    if s.empty:
        return []
    ts = s.index.to_series()
    new = (s != s.shift()) | (ts.diff() != INTERVAL)
    out = []
    for _, grp in s.groupby(new.cumsum()):
        out.append((grp.index[0], grp.index[-1] + INTERVAL, grp.iloc[0]))
    return out


def detect(
    status_by_asset: dict[str, pd.Series], dictionary: dict[str, dict], scope: str, setpoint: pd.Series | None = None
) -> list[dict]:
    events = []
    for asset, series in status_by_asset.items():
        for start, end, code in runs(series):
            entry = dictionary.get(code, {"normal": True})
            if entry.get("normal"):
                continue
            ev = {
                "asset_id": asset,
                "category": entry["category"],
                "cause_code": entry["cause_code"],
                "start_ts": start,
                "end_ts": end,
                "controllable": bool(entry["controllable"]),
                "confidence": "confirmed",
                "setpoint_kw": None,
                "evidence": {
                    "rules": ["status_code"],
                    "metrics": {"status": code, "scope": scope, "intervals": int((end - start) / INTERVAL)},
                },
            }
            if entry["category"] == "curtailment" and setpoint is not None:
                sp = setpoint[(setpoint.index >= start) & (setpoint.index < end)]
                ev["setpoint_kw"] = float(sp.min()) if len(sp) else None
            events.append(ev)
    return events
