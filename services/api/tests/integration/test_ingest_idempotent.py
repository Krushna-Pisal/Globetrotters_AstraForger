"""T-DATA-01: ingesting the same files twice leaves row counts and values unchanged."""

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from pipelines import kaggle as kaggle_step
from tests.kaggle_fixture import write_kaggle_fixture

pytestmark = pytest.mark.db

TABLES = ["measurement", "actual_output", "expected_output", "source_batch", "event"]


def _snapshot(conn):
    counts = {
        t: conn.execute(text(f"SELECT count(*) FROM {t} WHERE dataset_id = 'kaggle_p2_2020'")).scalar_one()  # noqa: S608
        for t in TABLES
    }
    digest = conn.execute(
        text(
            "SELECT md5(string_agg(asset_id || quantity || ts_start::text || coalesce(value::text,'') "
            "|| quality::text, ',' "
            "ORDER BY asset_id, quantity, ts_start)) FROM measurement WHERE dataset_id = 'kaggle_p2_2020'"
        )
    ).scalar_one()
    return counts, digest


def test_reingest_is_idempotent(migrated_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "data_dir", tmp_path / "data")
    d = write_kaggle_fixture(tmp_path / "raw", days=10, drop=7)
    with migrated_engine.begin() as conn:
        first = kaggle_step.ingest(conn, d)
    with migrated_engine.connect() as conn:
        snap1 = _snapshot(conn)
    with migrated_engine.begin() as conn:
        kaggle_step.ingest(conn, d)
    with migrated_engine.connect() as conn:
        snap2 = _snapshot(conn)
    assert snap1 == snap2
    assert snap1[0]["measurement"] > 0
    assert first["irradiance_unit_detected"] == "kW/m2"
    assert (tmp_path / "data" / "manifests" / "kaggle_p2_2020.json").exists()
