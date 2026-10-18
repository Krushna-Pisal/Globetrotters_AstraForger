"""Hourly weather -> 15-min intervals (docs/06 §5 step 2), and azimuth conventions (CLAUDE.md gotchas).

Hourly radiation is the mean of the preceding hour, stamped at hour end. The 15-min interval starting at s belongs to
the hour ending at floor(s, 1h) + 1h. Clear-sky index downscaling keeps the hourly mean exactly:
    k = GHI_h / mean(GHI_cs over the hour's 4 interval midpoints);  GHI_15 = k × GHI_cs(midpoint)
DHI keeps the hour's diffuse fraction; DNI closes the triangle at the 15-min sun position.
Temperature and wind are instantaneous at the hour stamp and are linearly interpolated to interval midpoints.
"""

import numpy as np
import pandas as pd
import pvlib

K_MAX = 1.5
CS_MIN = 1.0  # W/m²: hour treated as night below this mean clear-sky GHI
ZENITH_MAX = 87.0


def pvlib_azimuth_from_south_zero(aspect_deg: float) -> float:
    """Open-Meteo GTI / PVGIS `aspect` (0 = south, -90 = east) -> pvlib (180 = south, 90 = east)."""
    return (aspect_deg + 180.0) % 360.0


def south_zero_from_pvlib(azimuth_deg: float) -> float:
    a = (azimuth_deg - 180.0) % 360.0
    return a - 360.0 if a > 180.0 else a


def hour_end_label(interval_start: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return interval_start.floor("h") + pd.Timedelta(hours=1)


def downscale(hourly: pd.DataFrame, index: pd.DatetimeIndex, lat: float, lon: float) -> pd.DataFrame:
    """hourly: hour-end UTC index with ghi, dni, dhi, temp_air, wind_speed, precip_mm. index: 15-min interval starts."""
    loc = pvlib.location.Location(lat, lon, tz="UTC")
    mid = index + pd.Timedelta(minutes=7.5)
    cs = loc.get_clearsky(mid, model="ineichen")["ghi"].to_numpy()
    zen = loc.get_solarposition(mid)["apparent_zenith"].to_numpy()

    label = hour_end_label(index)
    h = hourly.reindex(label)
    if h[["ghi", "dhi"]].isna().any().any():
        missing = label[h["ghi"].isna()][:3]
        raise ValueError(f"hourly weather missing for hours ending {list(missing)}")
    cs_mean = pd.Series(cs).groupby(label.to_numpy()).transform("mean").to_numpy()
    ghi_h = h["ghi"].to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        k = np.where(cs_mean >= CS_MIN, np.clip(ghi_h / cs_mean, 0.0, K_MAX), 0.0)
        kd = np.where(ghi_h > 0, np.clip(h["dhi"].to_numpy() / ghi_h, 0.0, 1.0), 1.0)
    ghi = k * cs
    dhi = kd * ghi
    cosz = np.cos(np.radians(zen))
    dni = np.where(zen < ZENITH_MAX, np.clip((ghi - dhi) / np.maximum(cosz, 1e-3), 0.0, 1200.0), 0.0)

    stamps = hourly.index

    def interp(col: str) -> np.ndarray:
        return np.interp(mid.asi8, stamps.asi8, hourly[col].to_numpy())

    return pd.DataFrame(
        {
            "ghi": ghi,
            "dni": dni,
            "dhi": dhi,
            "temp_air": interp("temp_air"),
            "wind_speed": interp("wind_speed"),
            "precip_mm": h["precip_mm"].to_numpy() / 4.0,
        },
        index=pd.DatetimeIndex(index, name="ts_start"),
    )
