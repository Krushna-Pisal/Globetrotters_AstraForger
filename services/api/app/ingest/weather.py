"""Weather adapters with an on-disk cache (the only internet step; everything after runs offline).

- Open-Meteo archive (ERA5), primary for the synthetic year. Radiation = mean of the PRECEDING hour, stamped at
  hour end.
- NASA POWER hourly, fallback. Requested in UTC (time-standard=utc); radiation treated like Open-Meteo (hour-end mean).
- PVGIS TMY (via pvlib), for the baseline. Stamped hh:00 UTC; components close at the stamp, so it is the hour
  midpoint (D21).

Each fetch writes the raw response to data/raw/weather/ and an entry with sha256 + URL + attribution to data/manifests/.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from app.core.config import get_settings
from app.ingest.manifest import sha256_file, write_manifest

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_VARS = (
    "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m,wind_speed_10m,precipitation"
)
OPEN_METEO_ATTRIBUTION = (
    "Weather data by Open-Meteo.com (CC BY 4.0), ERA5 reanalysis, Copernicus Climate Change Service"
)
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
NASA_ATTRIBUTION = (
    "NASA Langley Research Center (LaRC) POWER Project, funded through the NASA Earth Science Directorate"
)
PVGIS_ATTRIBUTION = "PVGIS (c) European Union, 2001-2026"


def weather_dir() -> Path:
    d = get_settings().data_dir / "raw" / "weather"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch_open_meteo(lat: float, lon: float, start: str, end: str, path: Path) -> Path:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": OPEN_METEO_VARS,
        "timezone": "GMT",
        "wind_speed_unit": "ms",
    }
    r = requests.get(OPEN_METEO_URL, params=params, timeout=120)
    r.raise_for_status()
    path.write_text(json.dumps(r.json()), encoding="utf-8")
    write_manifest(
        "weather_" + path.stem,
        {
            "source": "open_meteo_archive",
            "url": r.url,
            "path": str(path.name),
            "sha256": sha256_file(path),
            "retrieved_at": datetime.now(UTC),
            "license": "CC BY 4.0",
            "attribution": OPEN_METEO_ATTRIBUTION,
            "timestamp_convention": "radiation = mean of preceding hour, hour-end",
        },
    )
    return path


def load_open_meteo(path: Path) -> pd.DataFrame:
    """Hourly frame indexed by hour-END UTC stamps: ghi, dni, dhi, temp_air, wind_speed, precip_mm."""
    h = json.loads(path.read_text(encoding="utf-8"))["hourly"]
    df = pd.DataFrame(
        {
            "ghi": h["shortwave_radiation"],
            "dni": h["direct_normal_irradiance"],
            "dhi": h["diffuse_radiation"],
            "temp_air": h["temperature_2m"],
            "wind_speed": h["wind_speed_10m"],
            "precip_mm": h["precipitation"],
        },
        index=pd.DatetimeIndex(pd.to_datetime(h["time"]), name="hour_end").tz_localize("UTC"),
    )
    return df.astype(float)


def fetch_nasa_power(lat: float, lon: float, start: str, end: str, path: Path) -> Path:
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF,T2M,WS10M,PRECTOTCORR",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start.replace("-", ""),
        "end": end.replace("-", ""),
        "format": "JSON",
        "time-standard": "utc",
    }
    r = requests.get(NASA_POWER_URL, params=params, timeout=300)
    r.raise_for_status()
    path.write_text(json.dumps(r.json()), encoding="utf-8")
    write_manifest(
        "weather_" + path.stem,
        {
            "source": "nasa_power_hourly",
            "url": r.url,
            "path": str(path.name),
            "sha256": sha256_file(path),
            "retrieved_at": datetime.now(UTC),
            "attribution": NASA_ATTRIBUTION,
            "time_standard": "utc",
        },
    )
    return path


def load_nasa_power(path: Path) -> pd.DataFrame:
    p = json.loads(path.read_text(encoding="utf-8"))["properties"]["parameter"]
    stamps = pd.to_datetime(list(p["T2M"].keys()), format="%Y%m%d%H").tz_localize("UTC")
    df = pd.DataFrame(
        {
            "ghi": list(p["ALLSKY_SFC_SW_DWN"].values()),
            "dni": list(p["ALLSKY_SFC_SW_DNI"].values()),
            "dhi": list(p["ALLSKY_SFC_SW_DIFF"].values()),
            "temp_air": list(p["T2M"].values()),
            "wind_speed": list(p["WS10M"].values()),
            "precip_mm": list(p["PRECTOTCORR"].values()),
        },
        index=pd.DatetimeIndex(stamps + pd.Timedelta(hours=1), name="hour_end"),
    ).astype(float)
    return df.where(df > -900)  # POWER uses -999 for missing


def fetch_pvgis_tmy(lat: float, lon: float, path: Path) -> Path:
    import pvlib

    data, months, inputs, meta = pvlib.iotools.get_pvgis_tmy(lat, lon, map_variables=True, timeout=120)
    payload = {
        "data": json.loads(data.to_json(orient="split", date_format="iso")),
        "months_selected": months,
        "inputs": inputs,
        "meta": meta,
    }
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")
    db = inputs.get("meteo_data", {})
    write_manifest(
        "weather_" + path.stem,
        {
            "source": "pvgis_tmy",
            "path": str(path.name),
            "sha256": sha256_file(path),
            "retrieved_at": datetime.now(UTC),
            "attribution": PVGIS_ATTRIBUTION,
            "radiation_db": db.get("radiation_db"),
            "meteo_db": db.get("meteo_db"),
            "year_min": db.get("year_min"),
            "year_max": db.get("year_max"),
            "months_selected": months,
            "timestamp_convention": "hh:00 UTC = hour midpoint; DNI cos z + DHI = GHI at the stamp (D21)",
        },
    )
    return path


def load_pvgis_tmy(path: Path) -> tuple[pd.DataFrame, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    d = payload["data"]
    df = pd.DataFrame(d["data"], columns=d["columns"], index=pd.to_datetime(d["index"], utc=True))
    return df[["ghi", "dni", "dhi", "temp_air", "wind_speed"]].astype(float), payload["inputs"]
