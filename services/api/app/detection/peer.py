"""Peer deviation rule (docs/02 §8.1, C12) and the peer_ratio metric.

Daily peer_ratio = inverter energy / median peer energy over eligible intervals (daylight, the inverter's data ok,
status normal). The rule compares each inverter with its own reference ratio (median of its first REFERENCE_DAYS
eligible days, D22), so a unit that is permanently a few % weaker is not re-flagged every week; a drop of the
normalised ratio below 0.95 for ≥ 3 consecutive days → underperformance, `suspected` ("symptom detected — inspect").
The raw peer_ratio stays the metric shown in the heatmap.
"""

import pandas as pd

from app.core.timeutil import local_date

THRESHOLD = 0.95
MIN_DAYS = 3
REFERENCE_DAYS = 14
MERGE_GAP_DAYS = 3  # runs separated by ≤ 3 days are one symptom (D22)


def daily_peer_ratio(actual: pd.DataFrame, daylight: pd.Series) -> pd.DataFrame:
    """actual: eligible rows only (asset_id, ts_start, e_kwh, quality); daylight: bool Series by ts_start.

    Returns a date x asset frame of ratios.
    """
    a = actual[actual["quality"] == "ok"]
    a = a[a["ts_start"].map(daylight).fillna(False).astype(bool)]
    wide = a.pivot(index="ts_start", columns="asset_id", values="e_kwh")
    median = wide.median(axis=1)
    peer = wide.notna().mul(median, axis=0).where(wide.notna())
    dates = local_date(wide.index).to_numpy()
    num = wide.groupby(dates).sum(min_count=1)
    den = peer.groupby(dates).sum(min_count=1)
    return (num / den).rename_axis("date")


def normalised(ratio: pd.DataFrame) -> pd.DataFrame:
    reference = ratio.apply(lambda s: s.dropna().iloc[:REFERENCE_DAYS].median())
    return ratio / reference


def detect(ratio: pd.DataFrame) -> list[dict]:
    """Runs of >= MIN_DAYS consecutive calendar days with normalised ratio below THRESHOLD per inverter."""
    events = []
    for asset, s in normalised(ratio).items():
        s = s.dropna()
        run: list = []
        for day, value in list(s.items()) + [(None, None)]:
            low = value is not None and value < THRESHOLD
            if low and run and (day - run[-1][0]).days == 1:
                run.append((day, value))
                continue
            if len(run) >= MIN_DAYS:
                vals = [v for _, v in run]
                events.append(
                    {
                        "asset_id": asset,
                        "first_day": run[0][0],
                        "last_day": run[-1][0],
                        "days": len(run),
                        "mean_ratio": round(sum(vals) / len(vals), 4),
                        "min_ratio": round(min(vals), 4),
                    }
                )
            run = [(day, value)] if low else []
    return merge(events)


def merge(events: list[dict]) -> list[dict]:
    out: list[dict] = []
    for e in sorted(events, key=lambda x: (x["asset_id"], x["first_day"])):
        prev = out[-1] if out else None
        if prev and prev["asset_id"] == e["asset_id"] and (e["first_day"] - prev["last_day"]).days <= MERGE_GAP_DAYS:
            n = prev["days"] + e["days"]
            prev["mean_ratio"] = round((prev["mean_ratio"] * prev["days"] + e["mean_ratio"] * e["days"]) / n, 4)
            prev["min_ratio"] = min(prev["min_ratio"], e["min_ratio"])
            prev["days"], prev["last_day"] = n, e["last_day"]
        else:
            out.append(dict(e))
    return out
