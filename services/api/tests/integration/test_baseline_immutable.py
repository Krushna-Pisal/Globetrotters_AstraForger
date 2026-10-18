"""T-BASE-01: UPDATE/DELETE on an approved row raises; PATCH returns 409.
T-BASE-02: approving v2 leaves v1 rows byte-identical and visible in history."""

from decimal import Decimal

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.api.deps import get_conn
from app.baseline import build
from app.core.auth import issue_token
from app.core.config import get_settings
from app.main import app
from app.twin.loader import load_plant
from tests.weather_fixture import clearsky_hourly

pytestmark = pytest.mark.db
PLANT = "BASETEST"


@pytest.fixture(scope="module")
def engine(migrated_engine):
    with migrated_engine.begin() as conn:
        conn.execute(text("ALTER TABLE baseline DISABLE TRIGGER baseline_immutable"))
        conn.execute(text("DELETE FROM baseline WHERE plant_id = :p"), {"p": PLANT})
        conn.execute(text("ALTER TABLE baseline ENABLE TRIGGER baseline_immutable"))
    return migrated_engine


def _rows(version: int, supersedes: int | None, scale: float = 1.0):
    cfg = yaml.safe_load((get_settings().configs_dir / "baseline" / "baseline_v1.yaml").read_text())["baseline"]
    cfg["energy_kwh"]["sanity_range_annual"] = [0, 1e12]
    plant = load_plant("THAR1") | {"id": PLANT}
    tmy = clearsky_hourly("2023-01-01 00:00", "2023-12-31 23:00")
    tmy.index = tmy.index - pd.Timedelta(hours=1)  # PVGIS-like hh:00 stamps
    tmy[["ghi", "dni", "dhi"]] *= scale
    rows, _ = build.build_rows(tmy, {}, plant, cfg, Decimal("170000000"), version, supersedes)
    return rows


def _snapshot(conn, version):
    return (
        conn.execute(
            text(
                "SELECT row_to_json(b)::text FROM baseline b WHERE plant_id = :p AND version = :v "
                "ORDER BY valid_month"
            ),
            {"p": PLANT, "v": version},
        )
        .scalars()
        .all()
    )


def test_approved_rows_are_immutable(engine):
    with engine.begin() as conn:
        build.save_draft(conn, _rows(1, None))
        build.approve(conn, PLANT, 1, "presenter")
    for sql in (
        "UPDATE baseline SET energy_p50_kwh = 1 WHERE plant_id = :p AND version = 1",
        "DELETE FROM baseline WHERE plant_id = :p AND version = 1",
    ):
        with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
            conn.execute(text(sql), {"p": PLANT})
    with pytest.raises(build.BaselineError), engine.begin() as conn:
        build.save_draft(conn, _rows(1, None))


def test_patch_returns_409(engine):
    def conn_override():
        with engine.begin() as conn:
            yield conn

    app.dependency_overrides[get_conn] = conn_override
    try:
        client = TestClient(app)
        token = issue_token("presenter")
        r = client.patch("/v1/baseline/1", params={"plant_id": PLANT}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 409
        assert r.json()["detail"] == "baseline_immutable"
    finally:
        app.dependency_overrides.clear()


def test_v2_leaves_v1_untouched(engine):
    with engine.connect() as conn:
        v1_before = _snapshot(conn, 1)
    with engine.begin() as conn:
        version, supersedes = build.next_version(conn, PLANT)
        assert (version, supersedes) == (2, 1)
        build.save_draft(conn, _rows(2, 1, scale=1.1))
        build.approve(conn, PLANT, 2, "presenter", reason="re-run with corrected weather")
    with engine.connect() as conn:
        assert _snapshot(conn, 1) == v1_before
        hist = build.versions(conn, PLANT)
    assert [h["version"] for h in hist] == [1, 2]
    assert all(h["status"] == "approved" for h in hist)
    assert hist[1]["supersedes"] == 1 and hist[1]["p50_kwh"] > hist[0]["p50_kwh"]
