"""T-REPRO-01 (generator part) and generator behaviour: SCADA-style faults, comms loss, soiling, ground truth."""

import numpy as np
import pandas as pd
import pytest

from app.core.timeutil import interval_index
from app.performance import weather15
from app.scenarios import generator
from app.twin.loader import load_plant
from pipelines.thar1 import load_scenario
from tests.weather_fixture import clearsky_hourly


def _run(seed: int | None = None, start="2024-04-08", end="2024-04-14"):
    scn = load_scenario("thar1_demo_2024")
    if seed is not None:
        scn["seed"] = seed
    idx = interval_index(start, end)
    hourly = clearsky_hourly(str(idx[0] - pd.Timedelta(hours=1)), str(idx[-1] + pd.Timedelta(hours=2)))
    return generator.generate(scn, load_plant("THAR1"), weather15.downscale(hourly, idx, 27.54, 71.91))


@pytest.fixture(scope="module")
def april():
    return _run()


def test_same_seed_identical(april):
    again = _run()
    assert np.array_equal(april.ac_kw, again.ac_kw)
    assert np.array_equal(april.meter_kwh, again.meter_kwh)
    assert april.ground_truth == again.ground_truth


def test_different_seed_differs(april):
    assert not np.array_equal(april.ac_kw, _run(seed=1).ac_kw)


def test_outage_reported_as_status_and_zero_power(april):
    j = april.inverters.index("INV-07")
    start = pd.Timestamp("2024-04-09 10:15", tz="Asia/Kolkata")
    end = pd.Timestamp("2024-04-12 10:15", tz="Asia/Kolkata")
    m = (april.index >= start) & (april.index < end)
    assert (april.ac_kw[m, j] == 0).all()
    assert set(april.status[m, j]) == {"FAULT_OVERTEMP"}
    assert set(april.status[~m, j]) == {"RUNNING"}
    e01 = next(e for e in april.ground_truth["events"] if e["id"] == "E01")
    assert e01["true_lost_kwh_delivery_point"] > 0


def test_silent_derate_has_no_status_code():
    out = _run(start="2024-09-02", end="2024-09-04")
    j = out.inverters.index("INV-17")
    assert set(out.status[:, j]) == {"RUNNING"}
    totals = out.ac_kw.sum(axis=0)
    relative = totals[j] / np.median(np.delete(totals, j)) / out.ground_truth["inverter_factors"]["INV-17"]
    assert relative < 0.95  # 8 % DC derate, partly hidden by clipping


def test_comms_loss_removes_rows_but_meter_counts():
    out = _run(start="2024-05-20", end="2024-05-21")
    j = out.inverters.index("INV-15")
    gap = (out.index >= pd.Timestamp("2024-05-20 12:00", tz="Asia/Kolkata")) & (
        out.index < pd.Timestamp("2024-05-20 16:00", tz="Asia/Kolkata")
    )
    assert not out.reported[gap, j].any() and out.reported[~gap, j].all()
    assert (np.diff(out.heartbeat[gap, j]) == 0).all()  # stalled
    assert out.ac_kw[gap, j].sum() > 0  # still producing, so the meter includes it
    assert out.meter_kwh[gap].sum() == pytest.approx(out.ac_kw[gap].sum() * 0.25 * 0.985, rel=0.01)


def test_missed_cleaning_extends_soiling():
    scn = load_scenario("thar1_demo_2024")
    days = list(pd.date_range("2024-04-01", "2024-05-31").date)
    soil, performed = generator.soiling_series(days, scn["soiling"], pd.Series(dtype=float))
    assert pd.Timestamp("2024-05-04").date() not in performed
    assert pd.Timestamp("2024-05-19").date() in performed
    assert soil[pd.Timestamp("2024-05-18").date()] > 0.06  # ~29 days of accumulation at 0.25 %/day
    assert soil[pd.Timestamp("2024-05-19").date()] == 0.0
