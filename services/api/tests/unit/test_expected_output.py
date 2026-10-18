"""T-PHYS-01/02/03: physical sanity of the pvlib chain, azimuth conventions, hourly-mean midpoint shift."""

import numpy as np
import pandas as pd
import pytest

from app.core.timeutil import interval_index
from app.performance import model, weather15
from app.twin.loader import load_plant
from tests.weather_fixture import clearsky_hourly


@pytest.fixture(scope="module")
def params():
    return model.ChainParams.from_plant(load_plant("THAR1"))


def _weather(start_local: str, end_local: str, **kw) -> pd.DataFrame:
    idx = interval_index(start_local, end_local)
    hourly = clearsky_hourly(str(idx[0] - pd.Timedelta(hours=1)), str(idx[-1] + pd.Timedelta(hours=2)), **kw)
    return weather15.downscale(hourly, idx, 27.54, 71.91)


# ---- T-PHYS-01
def test_night_is_zero_and_never_above_rating(params):
    w = _weather("2024-05-01", "2024-05-03")
    r = model.run_chain(w, params, 0.25)
    local_hour = r.index.tz_convert("Asia/Kolkata").hour
    night = (local_hour < 5) | (local_hour >= 20)
    assert (r.loc[night, "e_potential_kwh"] == 0).all()
    assert (r["p_ac_kw"] <= 2500.0 + 1e-9).all()
    assert r["e_potential_kwh"].max() > 0


def test_clipping_is_flagged(params):
    w = _weather("2024-01-15", "2024-01-16", temp=5.0, wind=6.0)  # cold, clear: DC/AC 1.2 clips at noon
    w[["ghi", "dni"]] *= 1.15
    r = model.run_chain(w, params, 0.25)
    assert r["clipped"].any()
    assert np.allclose(r.loc[r["clipped"], "p_ac_kw"], 2500.0)
    assert not r.loc[r["poa"] < 500, "clipped"].any()


def test_poa_exceeds_ghi_at_winter_noon(params):
    w = _weather("2024-12-21", "2024-12-22")
    r = model.run_chain(w, params, 0.25)
    noon = r.index.tz_convert("Asia/Kolkata").hour == 12
    assert (r.loc[noon, "poa"].to_numpy() > w.loc[noon, "ghi"].to_numpy()).all()


# ---- T-PHYS-02
def test_azimuth_conversion():
    assert weather15.pvlib_azimuth_from_south_zero(0) == 180
    assert weather15.pvlib_azimuth_from_south_zero(-90) == 90
    assert weather15.pvlib_azimuth_from_south_zero(90) == 270
    assert weather15.south_zero_from_pvlib(180) == 0
    assert weather15.south_zero_from_pvlib(90) == -90


def test_north_facing_yields_clearly_less(params):
    north = model.ChainParams.from_plant(load_plant("THAR1"), azimuth_override=0.0)
    totals = {}
    for name, p in (("south", params), ("north", north)):
        e = 0.0
        for month in range(1, 13):
            w = _weather(f"2024-{month:02d}-15", f"2024-{month:02d}-16")
            e += model.run_chain(w, p, 0.25)["e_potential_kwh"].sum()
        totals[name] = e
    assert totals["north"] < 0.9 * totals["south"]


# ---- T-PHYS-03
def test_hour_end_mean_maps_to_preceding_intervals():
    idx = pd.date_range("2024-04-09 04:00", periods=12, freq="15min", tz="UTC")  # 09:30–12:15 IST
    hourly = clearsky_hourly("2024-04-09 03:00", "2024-04-09 08:00")
    hourly[["ghi", "dni", "dhi"]] = 0.0
    hourly.loc[pd.Timestamp("2024-04-09 06:00", tz="UTC"), ["ghi", "dhi"]] = [600.0, 100.0]  # mean of 05:00–06:00
    w = weather15.downscale(hourly, idx, 27.54, 71.91)
    inside = (w.index >= pd.Timestamp("2024-04-09 05:00", tz="UTC")) & (
        w.index < pd.Timestamp("2024-04-09 06:00", tz="UTC")
    )
    assert (w.loc[inside, "ghi"] > 0).all()
    assert (w.loc[~inside, "ghi"] == 0).all()
    assert w.loc[inside, "ghi"].mean() == pytest.approx(600.0, rel=1e-9)
    assert w.loc[inside, "dhi"].sum() / w.loc[inside, "ghi"].sum() == pytest.approx(100 / 600)


def test_chain_uses_interval_midpoint(params):
    w = _weather("2024-03-20", "2024-03-21")
    r15 = model.run_chain(w, params, 0.25)
    shifted = w.copy()
    shifted.index = shifted.index + pd.Timedelta(minutes=7.5)
    r_mid = model.run_chain(shifted, params, 0.0)  # zero length: evaluates exactly at the given stamp
    assert np.allclose(r15["p_ac_kw"].to_numpy(), r_mid["p_ac_kw"].to_numpy())
