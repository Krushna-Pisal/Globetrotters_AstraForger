"""T-OM-01: A_E excludes grid/curtailment/no_data; LD example docs/02 §4.4 = ₹10.80 lakh; cap applies."""

from decimal import Decimal

import pandas as pd

from app.contracts.loader import load_om
from app.om import availability

T0 = pd.Timestamp("2024-06-18 05:00", tz="UTC")


def _frames():
    ts = [T0 + pd.Timedelta(minutes=15 * i) for i in range(8)]
    expected = pd.DataFrame({"asset_id": "P/INV-01", "ts_start": ts, "e_potential_kwh": 500.0})
    actual = pd.DataFrame(
        {
            "asset_id": "P/INV-01",
            "ts_start": ts,
            "e_kwh": [0.0, 0.0, 500.0, 500.0, 0.0, 0.0, None, 0.0],
            "quality": ["ok", "ok", "ok", "ok", "ok", "ok", "no_data", "ok"],
        }
    )
    events = pd.DataFrame(
        [
            {
                "id": 1,
                "asset_id": "P/INV-01",
                "category": "equipment_outage",
                "cause_code": "IGBT_OVERTEMP",
                "start_ts": ts[0],
                "end_ts": ts[2],
                "confidence": "confirmed",
            },
            {
                "id": 2,
                "asset_id": "P",
                "category": "grid_unavailability",
                "cause_code": "LINE_OUTAGE",
                "start_ts": ts[4],
                "end_ts": ts[5],
                "confidence": "confirmed",
            },
            {
                "id": 3,
                "asset_id": "P",
                "category": "curtailment",
                "cause_code": "SLDC_BACKDOWN",
                "start_ts": ts[5],
                "end_ts": ts[6],
                "confidence": "confirmed",
            },
            {
                "id": 4,
                "asset_id": "P/INV-01",
                "category": "equipment_outage",
                "cause_code": "IGBT_OVERTEMP",
                "start_ts": ts[7],
                "end_ts": ts[7] + pd.Timedelta(minutes=15),
                "confidence": "confirmed",
            },
        ]
    )
    return expected, actual, events


def test_availability_excludes_grid_curtailment_and_no_data():
    om = load_om()
    f = availability.interval_frame(*_frames(), om)
    assert list(f["excluded"]) == [False, False, False, False, True, True, True, False]
    a_e, loss, ep = availability.energy_based(f)
    assert ep == 5 * 500.0  # intervals 0,1,2,3,7 eligible
    assert loss == 3 * 500.0  # outages in 0,1,7
    assert a_e == 1 - 1500 / 2500


def test_ld_worked_example():
    om = load_om()
    ld = availability.liquidated_damages(Decimal("0.986"), Decimal("108000000"), om)
    assert ld.ld_kwh == Decimal("432000.000")
    assert ld.amount == Decimal("1080000.00")  # ₹10.80 lakh
    assert not ld.capped


def test_ld_cap():
    om = load_om()
    ld = availability.liquidated_damages(Decimal("0.95"), Decimal("108000000"), om)
    assert ld.amount == Decimal("3600000.00")  # 20 % of ₹1.80 cr fee
    assert ld.capped


def test_no_ld_when_guarantee_met():
    ld = availability.liquidated_damages(Decimal("0.995"), Decimal("108000000"), load_om())
    assert ld.amount == Decimal("0.00")
