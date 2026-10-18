"""T-DATA-03: no synthetic_* source_kind in a measured dataset and no `measured` in a synthetic one."""

import pandas as pd
import pytest
from sqlalchemy import text

from app.core.bulk import write_measurements
from app.core.config import get_settings
from app.core.timeutil import interval_index
from app.performance import weather15
from app.scenarios import generator
from app.twin.loader import load_plant
from pipelines import kaggle as kaggle_step
from pipelines.thar1 import load_scenario, write_scenario
from tests.kaggle_fixture import write_kaggle_fixture
from tests.weather_fixture import clearsky_hourly

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def loaded(migrated_engine, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("prov")
    settings = get_settings()
    old = settings.data_dir
    settings.data_dir = tmp / "data"
    try:
        with migrated_engine.begin() as conn:
            kaggle_step.ingest(conn, write_kaggle_fixture(tmp / "raw", days=10))
            scn = load_scenario("thar1_demo_2024")
            idx = interval_index("2024-04-09", "2024-04-10")
            hourly = clearsky_hourly(str(idx[0] - pd.Timedelta(hours=1)), str(idx[-1] + pd.Timedelta(hours=2)))
            out = generator.generate(scn, load_plant("THAR1"), weather15.downscale(hourly, idx, 27.54, 71.91))
            wfile = tmp / "weather.json"
            wfile.write_text("{}")
            write_scenario(conn, "thar1_demo_2024", scn, load_plant("THAR1"), out, wfile, "open_meteo_archive")
    finally:
        settings.data_dir = old
    return migrated_engine


def test_kinds_are_separated(loaded):
    with loaded.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT d.kind, m.source_kind::text, count(*) FROM measurement m JOIN dataset d ON d.id = m.dataset_id "
                "GROUP BY 1, 2"
            )
        ).all()
    kinds = {(k, s) for k, s, _ in rows}
    assert ("measured", "measured") in kinds and ("synthetic", "synthetic_scenario") in kinds
    assert not {s for k, s in kinds if k == "measured"} & {
        "synthetic_scenario",
        "synthetic_reference",
        "synthetic_contract",
    }
    assert "measured" not in {s for k, s in kinds if k == "synthetic"}


def test_writer_refuses_mixing(loaded):
    with loaded.begin() as conn:
        row = conn.execute(
            text(
                "SELECT asset_id, quantity, ts_start, batch_id FROM measurement "
                "WHERE dataset_id = 'kaggle_p2_2020' LIMIT 1"
            )
        ).one()
        bad = pd.DataFrame(
            [
                {
                    "dataset_id": "kaggle_p2_2020",
                    "asset_id": row.asset_id,
                    "quantity": "x",
                    "ts_start": row.ts_start,
                    "interval_s": 900,
                    "value": 1.0,
                    "value_text": None,
                    "unit": "kW",
                    "quality": "ok",
                    "source_kind": "synthetic_scenario",
                    "batch_id": row.batch_id,
                }
            ]
        )
        with pytest.raises(ValueError, match="synthetic"):
            write_measurements(conn, "kaggle_p2_2020", bad)
