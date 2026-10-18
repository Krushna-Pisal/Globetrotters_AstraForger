"""pvlib model chain (docs/02 §3.1). One implementation, used by expected output, the baseline and the scenario
generator, so weather is the only difference between P50 and E_bl_aw.

Per inverter, per interval, weather evaluated at the interval midpoint:
POA (Perez, tilt 25°, pvlib azimuth 180) -> SAPM cell temperature -> PVWatts DC (pdc0 3,000 kW, γ −0.35 %/°C)
-> structural DC losses -> degradation (1 − 0.005 × years since COD) -> PVWatts inverter (clips at 2,500 kW AC).
Delivery point = Σ inverters × (1 − 0.015) (applied by callers).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pvlib

from app.core.lineage import sha256_hash

MODEL_VERSION = "perf-1.0"


@dataclass(frozen=True)
class ChainParams:
    lat: float
    lon: float
    tilt: float
    azimuth_pvlib: float
    albedo: float
    pdc0_kw: float
    ac_kw: float
    eta_inv: float
    gamma: float
    structural_factor: float
    degradation_per_year: float
    cod: pd.Timestamp
    export_loss: float

    @classmethod
    def from_plant(cls, plant: dict, azimuth_override: float | None = None) -> "ChainParams":
        lr = plant["loss_register"]["structural"]
        s = (1 - lr["mismatch"]) * (1 - lr["dc_wiring"]) * (1 - lr["lid_and_nameplate"])
        inv = plant["inverter"]
        return cls(
            lat=plant["location"]["lat"],
            lon=plant["location"]["lon"],
            tilt=plant["array"]["tilt_deg"],
            azimuth_pvlib=plant["array"]["azimuth_deg_pvlib"] if azimuth_override is None else azimuth_override,
            albedo=plant["array"]["albedo"],
            pdc0_kw=inv["dc_kwp_each"],
            ac_kw=inv["ac_kw_each"],
            eta_inv=inv["eta_nom"],
            gamma=plant["module"]["gamma_pdc_per_c"],
            structural_factor=s,
            degradation_per_year=plant["loss_register"]["degradation"]["annual_fraction"],
            cod=pd.Timestamp(plant["cod"]).tz_localize(plant["location"]["tz"]).tz_convert("UTC"),
            export_loss=lr["export_to_delivery_point"],
        )

    def digest(self) -> str:
        return sha256_hash({k: str(v) for k, v in self.__dict__.items()})


def dc_chain(weather: pd.DataFrame, p: ChainParams, interval_h: float) -> pd.DataFrame:
    """weather: index = interval starts (UTC); ghi, dni, dhi, temp_air, wind_speed. Returns poa, t_cell, p_dc_kw."""
    mid = weather.index + pd.Timedelta(hours=interval_h / 2)
    loc = pvlib.location.Location(p.lat, p.lon, tz="UTC")
    sp = loc.get_solarposition(mid)
    dni_extra = pvlib.irradiance.get_extra_radiation(mid)
    airmass = pvlib.atmosphere.get_relative_airmass(sp["apparent_zenith"].to_numpy())
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=p.tilt,
        surface_azimuth=p.azimuth_pvlib,
        solar_zenith=sp["apparent_zenith"].to_numpy(),
        solar_azimuth=sp["azimuth"].to_numpy(),
        dni=weather["dni"].to_numpy(),
        ghi=weather["ghi"].to_numpy(),
        dhi=weather["dhi"].to_numpy(),
        dni_extra=dni_extra.to_numpy(),
        airmass=airmass,
        model="perez",
        albedo=p.albedo,
    )
    poa_global = np.clip(np.nan_to_num(np.asarray(poa["poa_global"], dtype=float)), 0.0, None)
    sapm = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_polymer"]
    t_cell = pvlib.temperature.sapm_cell(
        poa_global, weather["temp_air"].to_numpy(), weather["wind_speed"].to_numpy(), **sapm
    )
    p_dc = pvlib.pvsystem.pvwatts_dc(poa_global, t_cell, pdc0=p.pdc0_kw, gamma_pdc=p.gamma)
    years = (mid - p.cod).total_seconds().to_numpy() / (365.25 * 86400)
    p_dc = np.clip(p_dc * p.structural_factor * (1 - p.degradation_per_year * years), 0.0, None)
    return pd.DataFrame(
        {"poa": poa_global, "t_cell": np.asarray(t_cell, dtype=float), "p_dc_kw": p_dc}, index=weather.index
    )


def ac_from_dc(p_dc_kw: np.ndarray, p: ChainParams) -> np.ndarray:
    """PVWatts inverter; clips at eta × pdc0 = ac_kw."""
    pdc0 = p.ac_kw / p.eta_inv
    ac = pvlib.inverter.pvwatts(np.asarray(p_dc_kw, dtype=float), pdc0=pdc0, eta_inv_nom=p.eta_inv)
    return np.clip(np.nan_to_num(ac), 0.0, p.ac_kw)


def run_chain(weather: pd.DataFrame, p: ChainParams, interval_h: float) -> pd.DataFrame:
    """Per-inverter E_potential for one nominal inverter (all THAR1 inverters are identical)."""
    dc = dc_chain(weather, p, interval_h)
    ac = ac_from_dc(dc["p_dc_kw"].to_numpy(), p)
    dc["p_ac_kw"] = ac
    dc["clipped"] = ac >= p.ac_kw - 1e-6
    dc["e_potential_kwh"] = ac * interval_h
    return dc
