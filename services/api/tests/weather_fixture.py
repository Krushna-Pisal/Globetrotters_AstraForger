"""Clear-sky hourly weather for tests (no network). Hour-end stamps like Open-Meteo."""

import pandas as pd
import pvlib


def clearsky_hourly(
    start_utc: str,
    end_utc: str,
    lat: float = 27.54,
    lon: float = 71.91,
    temp: float = 25.0,
    wind: float = 2.0,
    precip_mm: float = 0.0,
) -> pd.DataFrame:
    ends = pd.date_range(pd.Timestamp(start_utc).floor("h"), pd.Timestamp(end_utc).ceil("h"), freq="h", tz="UTC")
    loc = pvlib.location.Location(lat, lon, tz="UTC")
    cs = loc.get_clearsky(ends - pd.Timedelta(minutes=30), model="ineichen")  # mean of the preceding hour ≈ midpoint
    return pd.DataFrame(
        {
            "ghi": cs["ghi"].to_numpy(),
            "dni": cs["dni"].to_numpy(),
            "dhi": cs["dhi"].to_numpy(),
            "temp_air": temp,
            "wind_speed": wind,
            "precip_mm": precip_mm,
        },
        index=pd.DatetimeIndex(ends, name="hour_end"),
    )
