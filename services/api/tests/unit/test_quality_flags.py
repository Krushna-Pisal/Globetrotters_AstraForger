"""T-DATA-04: night output, over-rating, gaps and duplicates get the right flags; raw values untouched."""

import pandas as pd

from app.ingest import kaggle
from app.quality import flags, validated
from tests.kaggle_fixture import write_kaggle_fixture

T0 = pd.Timestamp("2024-04-09 00:00", tz="UTC")


def _rows():
    ts = [T0 + pd.Timedelta(minutes=15 * i) for i in range(4)]
    return pd.DataFrame(
        [
            {"asset_id": "WS", "quantity": "poa_wm2", "ts_start": ts[0], "value": 0.0},  # night
            {"asset_id": "WS", "quantity": "poa_wm2", "ts_start": ts[1], "value": 800.0},
            {"asset_id": "WS", "quantity": "poa_wm2", "ts_start": ts[2], "value": 1600.0},  # impossible
            {"asset_id": "WS", "quantity": "poa_wm2", "ts_start": ts[3], "value": -5.0},
            {"asset_id": "I1", "quantity": "ac_power_kw", "ts_start": ts[0], "value": 50.0},  # night > 1 %
            {"asset_id": "I1", "quantity": "ac_power_kw", "ts_start": ts[1], "value": 1000.0},
            {"asset_id": "I2", "quantity": "ac_power_kw", "ts_start": ts[1], "value": 1100.0},  # > 1.02 × 1000
            {"asset_id": "I2", "quantity": "ac_power_kw", "ts_start": ts[0], "value": 5.0},  # night ≤ 1 %
        ]
    )


def test_flags():
    df = _rows()
    before = df.copy()
    q = flags.flag_measurements(df, rated_ac_kw=1000.0)
    assert list(q) == ["ok", "ok", "suspect", "suspect", "suspect", "ok", "suspect", "ok"]
    pd.testing.assert_frame_equal(df, before)  # raw rows untouched


def test_gap_is_no_data_in_actual_output():
    meas = _rows()
    meas["quality"] = "ok"
    meas["value_text"] = None
    index = pd.date_range(T0, periods=4, freq="15min")
    act = validated.energy_actual(meas, ["I1"], index, "ds")
    assert list(act["quality"]) == ["ok", "ok", "no_data", "no_data"]
    assert act["e_kwh"].iloc[1] == 250.0  # 1000 kW × 0.25 h
    assert act["e_kwh"].iloc[2:].isna().all()


def test_stalled_heartbeat_is_no_data():
    index = pd.date_range(T0, periods=3, freq="15min")
    meas = pd.DataFrame(
        [
            {
                "asset_id": "I1",
                "quantity": "ac_power_kw",
                "ts_start": t,
                "value": 100.0,
                "quality": "ok",
                "value_text": None,
            }
            for t in index
        ]
        + [
            {"asset_id": "I1", "quantity": "heartbeat", "ts_start": t, "value": v, "quality": "ok", "value_text": None}
            for t, v in zip(index, [1.0, 2.0, 2.0], strict=True)
        ]
    )
    act = validated.energy_actual(meas, ["I1"], index, "ds")
    assert list(act["quality"]) == ["ok", "ok", "no_data"]


def test_duplicates_counted_and_first_kept(tmp_path):
    d = write_kaggle_fixture(tmp_path, days=1, duplicate=True)
    gen = kaggle.parse_file(d / "Plant_2_Generation_Data.csv")
    assert kaggle.duplicate_count(gen) == 1
    key_map = {k: k for k in gen["SOURCE_KEY"].unique()}
    m = kaggle.generation_measurements(gen, key_map, include_dc=True)
    assert not m.duplicated(["asset_id", "quantity", "ts_start"]).any()


def test_gap_report(tmp_path):
    d = write_kaggle_fixture(tmp_path, days=1, drop=10)
    gen = kaggle.parse_file(d / "Plant_2_Generation_Data.csv")
    rep = kaggle.gap_report(gen)
    assert sum(v["missing"] for v in rep.values()) == 10
