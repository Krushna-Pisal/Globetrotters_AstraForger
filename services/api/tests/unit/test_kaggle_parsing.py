"""T-DATA-02: explicit date formats per file; 15-min monotonic index; irradiance units; AC/DC ratio flags Plant 1."""

import shutil

import pandas as pd
import pytest

from app.core.config import get_settings
from app.ingest import kaggle
from tests.kaggle_fixture import write_kaggle_fixture


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory):
    return write_kaggle_fixture(tmp_path_factory.mktemp("kaggle"), days=2)


def test_explicit_format_per_file(fixture_dir):
    assert kaggle.DATE_FORMATS["Plant_1_Generation_Data.csv"] == "%d-%m-%Y %H:%M"
    p1 = kaggle.parse_file(fixture_dir / "Plant_1_Generation_Data.csv")
    p2 = kaggle.parse_file(fixture_dir / "Plant_2_Generation_Data.csv")
    assert p1["ts_start"].min() == p2["ts_start"].min()
    # IST midnight 15 May = 18:30 UTC 14 May
    assert p2["ts_start"].min() == pd.Timestamp("2020-05-14 18:30", tz="UTC")


def test_wrong_format_is_rejected(fixture_dir):
    with pytest.raises(kaggle.KaggleFormatError):
        kaggle.parse_file(fixture_dir / "Plant_1_Generation_Data.csv", date_format="%Y-%m-%d %H:%M:%S")


def test_unknown_file_needs_explicit_format(fixture_dir, tmp_path):
    shutil.copy(fixture_dir / "Plant_2_Generation_Data.csv", tmp_path / "other.csv")
    with pytest.raises(kaggle.KaggleFormatError):
        kaggle.parse_file(tmp_path / "other.csv")


def test_off_grid_timestamp_rejected(fixture_dir, tmp_path):
    df = pd.read_csv(fixture_dir / "Plant_2_Weather_Sensor_Data.csv")
    df.loc[3, "DATE_TIME"] = "2020-05-15 00:50:00"
    df.to_csv(tmp_path / "Plant_2_Weather_Sensor_Data.csv", index=False)
    with pytest.raises(kaggle.KaggleFormatError):
        kaggle.parse_file(tmp_path / "Plant_2_Weather_Sensor_Data.csv")


def test_monotonic_15min_index(fixture_dir):
    df = kaggle.parse_file(fixture_dir / "Plant_2_Generation_Data.csv")
    steps = df.groupby("SOURCE_KEY")["ts_start"].diff().dropna()
    assert (steps == pd.Timedelta(minutes=15)).all()


def test_irradiance_unit_detection():
    assert kaggle.irradiance_unit(pd.Series([0, 0.5, 1.22])) == ("kW/m2", 1000.0)
    assert kaggle.irradiance_unit(pd.Series([0, 500, 1080])) == ("W/m2", 1.0)


def test_ac_dc_ratio_flags_plant_1(fixture_dir):
    p1 = kaggle.parse_file(fixture_dir / "Plant_1_Generation_Data.csv")
    p2 = kaggle.parse_file(fixture_dir / "Plant_2_Generation_Data.csv")
    assert not kaggle.dc_usable(kaggle.ac_dc_ratio(p1))
    assert kaggle.dc_usable(kaggle.ac_dc_ratio(p2))


REAL = get_settings().data_dir / "raw" / "kaggle"


@pytest.mark.skipif(not (REAL / "Plant_2_Generation_Data.csv").exists(), reason="real Kaggle files not downloaded")
def test_real_files_match_known_facts():
    p2 = kaggle.parse_file(REAL / "Plant_2_Generation_Data.csv")
    w2 = kaggle.parse_file(REAL / "Plant_2_Weather_Sensor_Data.csv")
    p1 = kaggle.parse_file(REAL / "Plant_1_Generation_Data.csv")
    assert p2["SOURCE_KEY"].nunique() == 22
    assert kaggle.irradiance_unit(w2["IRRADIATION"])[0] == "kW/m2"
    assert 0.97 < kaggle.ac_dc_ratio(p2) < 0.99
    assert kaggle.ac_dc_ratio(p1) < 0.2
