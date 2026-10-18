"""Kaggle 'Solar Power Generation Data' adapter (docs/06 §4, CLAUDE.md gotchas).

Each file is parsed with an explicit date format (they differ between files), timestamps are local IST converted
to UTC interval starts, irradiance units are detected from the maximum, and the AC/DC ratio is checked.
Cumulative yield channels are stored as-is and never summed as power.
"""

from pathlib import Path

import pandas as pd

from app.core.timeutil import INTERVAL, INTERVAL_H, PLANT_TZ

DATE_FORMATS = {
    "Plant_1_Generation_Data.csv": "%d-%m-%Y %H:%M",
    "Plant_1_Weather_Sensor_Data.csv": "%Y-%m-%d %H:%M:%S",
    "Plant_2_Generation_Data.csv": "%Y-%m-%d %H:%M:%S",
    "Plant_2_Weather_Sensor_Data.csv": "%Y-%m-%d %H:%M:%S",
}
GENERATION_COLUMNS = ["DATE_TIME", "PLANT_ID", "SOURCE_KEY", "DC_POWER", "AC_POWER", "DAILY_YIELD", "TOTAL_YIELD"]
WEATHER_COLUMNS = ["DATE_TIME", "PLANT_ID", "SOURCE_KEY", "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"]
AC_DC_USABLE = (0.90, 1.0)


class KaggleFormatError(ValueError):
    pass


def parse_file(path: Path, date_format: str | None = None) -> pd.DataFrame:
    """Read one Kaggle CSV with its explicit date format; add `ts_start` (UTC). Asserts a 15-min grid per key."""
    fmt = date_format or DATE_FORMATS.get(path.name)
    if fmt is None:
        raise KaggleFormatError(f"no explicit date format registered for {path.name}")
    df = pd.read_csv(path)
    expected = GENERATION_COLUMNS if "AC_POWER" in df.columns else WEATHER_COLUMNS
    if list(df.columns) != expected:
        raise KaggleFormatError(f"{path.name}: unexpected columns {list(df.columns)}")
    try:
        local = pd.to_datetime(df["DATE_TIME"], format=fmt)
    except ValueError as exc:
        raise KaggleFormatError(f"{path.name}: dates do not match {fmt!r}") from exc
    df["ts_start"] = local.dt.tz_localize(PLANT_TZ).dt.tz_convert("UTC")
    if not ((local.dt.minute % 15 == 0) & (local.dt.second == 0)).all():
        raise KaggleFormatError(f"{path.name}: timestamps are not on the 15-min grid")
    df = df.sort_values(["SOURCE_KEY", "ts_start"], kind="stable").reset_index(drop=True)
    assert_monotonic(df)
    return df


def assert_monotonic(df: pd.DataFrame) -> None:
    """Strictly increasing per key after removing exact duplicate timestamps (those are reported separately)."""
    dedup = df.drop_duplicates(["SOURCE_KEY", "ts_start"])
    steps = dedup.groupby("SOURCE_KEY")["ts_start"].diff().dropna()
    if (steps <= pd.Timedelta(0)).any() or ((steps % INTERVAL) != pd.Timedelta(0)).any():
        raise KaggleFormatError("index is not a monotonic 15-min series")


def full_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.date_range(df["ts_start"].min(), df["ts_start"].max(), freq=INTERVAL)


def irradiance_unit(series: pd.Series) -> tuple[str, float]:
    """Max ≈ 1.0–1.3 → kW/m² (scale 1000); otherwise W/m²."""
    peak = float(series.max())
    return ("kW/m2", 1000.0) if peak <= 1.5 else ("W/m2", 1.0)


def ac_dc_ratio(gen: pd.DataFrame) -> float:
    producing = gen[gen["DC_POWER"] > 0]
    return float(producing["AC_POWER"].sum() / producing["DC_POWER"].sum())


def dc_usable(ratio: float) -> bool:
    return AC_DC_USABLE[0] <= ratio <= AC_DC_USABLE[1]


def gap_report(df: pd.DataFrame) -> dict:
    idx = full_index(df)
    out = {}
    for key, g in df.drop_duplicates(["SOURCE_KEY", "ts_start"]).groupby("SOURCE_KEY"):
        present = pd.DatetimeIndex(g["ts_start"])
        missing = idx.difference(present)
        runs = (missing.to_series().diff() != INTERVAL).cumsum() if len(missing) else pd.Series(dtype=int)
        longest = int(runs.value_counts().max()) if len(missing) else 0
        out[key] = {
            "expected": len(idx),
            "present": len(present),
            "missing": len(missing),
            "coverage": round(len(present) / len(idx), 4),
            "longest_gap_intervals": longest,
        }
    return out


def duplicate_count(df: pd.DataFrame) -> int:
    return int(df.duplicated(["SOURCE_KEY", "ts_start"]).sum())


def daily_yield_check(gen: pd.DataFrame, tolerance: float = 0.02) -> dict:
    """Per inverter-day: Σ AC_POWER × 0.25 h vs end-of-day DAILY_YIELD (cumulative within the day)."""
    g = gen.drop_duplicates(["SOURCE_KEY", "ts_start"]).copy()
    g["date"] = g["ts_start"].dt.tz_convert(PLANT_TZ).dt.date
    agg = g.groupby(["SOURCE_KEY", "date"]).agg(
        e_power=("AC_POWER", lambda s: float((s * INTERVAL_H).sum())), e_yield=("DAILY_YIELD", "max")
    )
    agg = agg[agg["e_yield"] > 0]
    rel = (agg["e_power"] - agg["e_yield"]).abs() / agg["e_yield"]
    flagged = rel[rel > tolerance]
    return {
        "inverter_days": int(len(rel)),
        "median_rel_diff": round(float(rel.median()), 4) if len(rel) else None,
        "flagged_days": int(len(flagged)),
        "flagged_share": round(float(len(flagged) / len(rel)), 4) if len(rel) else None,
        "note": "days with gaps under-count Σ power; DAILY_YIELD is the inverter's own counter",
    }


def generation_measurements(gen: pd.DataFrame, key_to_asset: dict[str, str], include_dc: bool) -> pd.DataFrame:
    """Long measurement frame (quality filled later) for inverter channels."""
    g = gen.drop_duplicates(["SOURCE_KEY", "ts_start"], keep="first")
    unknown = set(g["SOURCE_KEY"]) - set(key_to_asset)
    if unknown:
        raise KaggleFormatError(f"source keys missing from the plant config: {sorted(unknown)}")
    channels = [
        ("AC_POWER", "ac_power_kw", "kW"),
        ("DAILY_YIELD", "daily_yield_kwh", "kWh"),
        ("TOTAL_YIELD", "total_yield_kwh", "kWh"),
    ]
    if include_dc:
        channels.append(("DC_POWER", "dc_power_kw", "kW"))
    frames = []
    for col, quantity, unit in channels:
        frames.append(
            pd.DataFrame(
                {
                    "asset_id": g["SOURCE_KEY"].map(key_to_asset).to_numpy(),
                    "quantity": quantity,
                    "ts_start": g["ts_start"].to_numpy(),
                    "value": g[col].astype(float).to_numpy(),
                    "unit": unit,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def weather_measurements(ws: pd.DataFrame, asset_id: str) -> pd.DataFrame:
    w = ws.drop_duplicates(["SOURCE_KEY", "ts_start"], keep="first")
    _, scale = irradiance_unit(w["IRRADIATION"])
    channels = [
        # Real-data mode: the plant's irradiance sensor is used as plane-of-array irradiance (labelled assumption).
        ("IRRADIATION", "poa_wm2", "W/m2", scale),
        ("MODULE_TEMPERATURE", "t_mod_c", "degC", 1.0),
        ("AMBIENT_TEMPERATURE", "t_amb_c", "degC", 1.0),
    ]
    frames = [
        pd.DataFrame(
            {
                "asset_id": asset_id,
                "quantity": q,
                "ts_start": w["ts_start"].to_numpy(),
                "value": (w[col].astype(float) * s).to_numpy(),
                "unit": unit,
            }
        )
        for col, q, unit, s in channels
    ]
    return pd.concat(frames, ignore_index=True)
