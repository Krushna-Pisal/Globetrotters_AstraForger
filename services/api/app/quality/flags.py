"""Per-measurement quality flags (docs/02 §2.3). Raw values are never changed; only the flag is set.

Duplicates cannot coexist in `measurement` (PK); the adapter keeps the first and the count goes in the report.
"""

import pandas as pd

NIGHT_FRACTION = 0.01  # night output > 1 % of rated → suspect
OVER_RATING = 1.02  # output > 1.02 × rated AC → suspect
IRR_MIN, IRR_MAX = 0.0, 1500.0


def flag_measurements(df: pd.DataFrame, rated_ac_kw: float, irradiance_quantity: str = "poa_wm2") -> pd.Series:
    """Return a quality Series aligned with `df` (long format: asset_id, quantity, ts_start, value)."""
    quality = pd.Series("ok", index=df.index, dtype=object)
    quality[df["value"].isna() & df["quantity"].ne("status")] = "no_data"

    irr = df[df["quantity"] == irradiance_quantity]
    bad_irr = irr.index[(irr["value"] < IRR_MIN) | (irr["value"] > IRR_MAX)]
    quality[bad_irr] = "suspect"

    night_ts = set(irr.loc[irr["value"] <= 0, "ts_start"])
    ac = df[df["quantity"] == "ac_power_kw"]
    night = ac.index[ac["ts_start"].isin(night_ts) & (ac["value"] > NIGHT_FRACTION * rated_ac_kw)]
    over = ac.index[ac["value"] > OVER_RATING * rated_ac_kw]
    quality[night] = "suspect"
    quality[over] = "suspect"
    return quality


def summarize(quality: pd.Series, df: pd.DataFrame) -> dict:
    counts = pd.crosstab(df["quantity"], quality)
    return {q: {k: int(v) for k, v in row.items() if v} for q, row in counts.iterrows()}
