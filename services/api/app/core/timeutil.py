"""Time conventions (CLAUDE.md): UTC storage, interval-start stamps, 15-min intervals, plant display tz Asia/Kolkata."""

import pandas as pd

PLANT_TZ = "Asia/Kolkata"
INTERVAL = pd.Timedelta(minutes=15)
INTERVAL_H = 0.25


def interval_index(start_local: str, end_local: str, tz: str = PLANT_TZ, freq: str = "15min") -> pd.DatetimeIndex:
    """UTC interval starts covering [start_local, end_local) in the plant's local time."""
    start = pd.Timestamp(start_local)
    end = pd.Timestamp(end_local)
    start = start.tz_localize(tz) if start.tzinfo is None else start
    end = end.tz_localize(tz) if end.tzinfo is None else end
    return pd.date_range(start, end, freq=freq, inclusive="left").tz_convert("UTC")


def local_month(ts_utc: pd.Series | pd.DatetimeIndex, tz: str = PLANT_TZ) -> pd.Series:
    """First day (date) of the local calendar month for each UTC timestamp."""
    local = pd.DatetimeIndex(ts_utc).tz_convert(tz)
    return pd.Series(local.to_period("M").to_timestamp().date, index=getattr(ts_utc, "index", None))


def local_date(ts_utc: pd.Series | pd.DatetimeIndex, tz: str = PLANT_TZ) -> pd.Series:
    local = pd.DatetimeIndex(ts_utc).tz_convert(tz)
    return pd.Series(local.date, index=getattr(ts_utc, "index", None))
