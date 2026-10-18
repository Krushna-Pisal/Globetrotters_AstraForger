"""M0 schema matches docs/04 §1–§2."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core import models

pytestmark = pytest.mark.db

ENUMS = {
    "source_kind": models.SOURCE_KINDS,
    "quality_flag": models.QUALITY_FLAGS,
    "event_category": models.EVENT_CATEGORIES,
    "confidence": models.CONFIDENCES,
    "contract_kind": models.CONTRACT_KINDS,
    "wo_status": models.WO_STATUSES,
}


@pytest.mark.parametrize("name,labels", ENUMS.items())
def test_enum_labels_match_models(migrated_engine, name, labels):
    with migrated_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = :n ORDER BY e.enumsortorder"
            ),
            {"n": name},
        ).scalars()
        assert tuple(rows) == labels


def test_m0_tables_exist(migrated_engine):
    with migrated_engine.connect() as conn:
        tables = set(conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
    assert {"dataset", "source_batch", "asset_template", "asset", "alembic_version"} <= tables


def test_dataset_kind_is_measured_or_synthetic(migrated_engine):
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        conn.execute(text("INSERT INTO dataset (id, plant_id, kind, config) VALUES ('x', 'THAR1', 'mixed', '{}')"))


def test_asset_hierarchy_and_template_fk(migrated_engine):
    with migrated_engine.begin() as conn:
        conn.execute(text("INSERT INTO asset_template VALUES ('solar_pv_fixed_tilt@1', 'plant', '{}')"))
        conn.execute(
            text(
                "INSERT INTO asset (id, plant_id, parent_id, kind, template_id, name) VALUES "
                "('THAR1', 'THAR1', NULL, 'plant', 'solar_pv_fixed_tilt@1', 'Thar-1'),"
                "('THAR1/B2', 'THAR1', 'THAR1', 'block', 'solar_pv_fixed_tilt@1', 'B2')"
            )
        )
        attrs = conn.execute(text("SELECT attrs FROM asset WHERE id = 'THAR1/B2'")).scalar_one()
        assert attrs == {}
        conn.execute(text("DELETE FROM asset"))
        conn.execute(text("DELETE FROM asset_template"))
    with pytest.raises(IntegrityError), migrated_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO asset (id, plant_id, parent_id, kind, template_id, name) "
                "VALUES ('ORPHAN', 'THAR1', 'NOPE', 'block', 'solar_pv_fixed_tilt@1', 'x')"
            )
        )
