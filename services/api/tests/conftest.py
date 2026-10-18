from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.main import app

API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def migrated_engine() -> Iterator[Engine]:
    """A fresh test database (never the demo one), migrated to head."""
    url = make_url(get_settings().test_database_url)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def demo_engine(migrated_engine) -> Engine:
    """April 2024 of THAR1 through quality -> ... -> finance in the test DB (clear-sky weather), plus demo users."""
    from decimal import Decimal

    import pandas as pd
    import yaml

    from app.baseline import build as baseline
    from app.core.timeutil import interval_index
    from app.performance import weather15
    from app.scenarios import generator
    from app.twin.loader import load_plant
    from pipelines import m3, thar1, users
    from tests.weather_fixture import clearsky_hourly

    plant = load_plant("THAR1")
    scn = thar1.load_scenario("thar1_demo_2024")
    idx = interval_index("2024-04-01", "2024-05-01")
    hourly = clearsky_hourly(str(idx[0] - pd.Timedelta(hours=1)), str(idx[-1] + pd.Timedelta(hours=2)))
    out = generator.generate(scn, plant, weather15.downscale(hourly, idx, 27.54, 71.91))
    wfile = API_DIR / "tests" / ".weather_fixture.json"
    wfile.write_text("{}")
    cfg = yaml.safe_load((get_settings().configs_dir / "baseline" / "baseline_v1.yaml").read_text())["baseline"]
    cfg["energy_kwh"]["sanity_range_annual"] = [0, 1e12]
    tmy = clearsky_hourly("2023-01-01 00:00", "2023-12-31 23:00")
    tmy.index = tmy.index - pd.Timedelta(hours=1)
    with migrated_engine.begin() as conn:
        thar1.write_scenario(conn, "thar1_demo_2024", scn, plant, out, wfile, "open_meteo_archive")
        version, sup = baseline.next_version(conn, "THAR1")
        rows, _ = baseline.build_rows(tmy, {}, plant, cfg, Decimal("170000000"), version, sup)
        baseline.save_draft(conn, rows)
        baseline.approve(conn, "THAR1", version, "test")
        users.seed(conn)
    wfile.unlink()
    for step in (
        thar1.step_quality,
        thar1.step_expected,
        thar1.step_detect,
        m3.step_accounting,
        m3.step_settlement,
        m3.step_om,
        m3.step_finance,
    ):
        with migrated_engine.begin() as conn:
            step(conn, "thar1_demo_2024")
    return migrated_engine


@pytest.fixture
def api(demo_engine) -> Iterator[TestClient]:
    """TestClient whose requests use the test database."""
    from app.api.deps import get_conn

    def conn_override():
        with demo_engine.begin() as conn:
            yield conn

    app.dependency_overrides[get_conn] = conn_override
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
