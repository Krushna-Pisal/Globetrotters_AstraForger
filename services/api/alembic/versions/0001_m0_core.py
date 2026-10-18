"""M0 core: docs/04 §1 enumerations and §2 identity, twin, provenance tables.

Revision ID: 0001_m0_core
Revises:
Create Date: 2026-10-18
"""

from alembic import op

revision = "0001_m0_core"
down_revision = None
branch_labels = None
depends_on = None

# DDL copied from docs/04_DATA_MODEL.md (names are binding).
UPGRADE = """
CREATE TYPE source_kind AS ENUM ('measured','weather_estimated','modeled','synthetic_scenario',
  'synthetic_reference','synthetic_contract','derived','operator');
CREATE TYPE quality_flag AS ENUM ('ok','estimated','no_data','suspect');
CREATE TYPE event_category AS ENUM ('equipment_outage','grid_unavailability','curtailment','comms_loss',
  'underperformance','cleaning','other');
CREATE TYPE confidence AS ENUM ('confirmed','suspected');
CREATE TYPE contract_kind AS ENUM ('ppa','om','loan');
CREATE TYPE wo_status AS ENUM ('open','acknowledged','onsite','restored','verified');

CREATE TABLE dataset (
  id            text PRIMARY KEY,
  plant_id      text NOT NULL,
  kind          text NOT NULL CONSTRAINT dataset_kind_check CHECK (kind IN ('measured','synthetic')),
  seed          bigint,
  config        jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_batch (
  id            uuid PRIMARY KEY,
  dataset_id    text NOT NULL REFERENCES dataset(id),
  source_name   text NOT NULL,
  url           text, license text,
  sha256        text NOT NULL,
  retrieved_at  timestamptz NOT NULL,
  source_kind   source_kind NOT NULL,
  notes         text
);

CREATE TABLE asset_template (id text PRIMARY KEY, kind text NOT NULL, schema jsonb NOT NULL);

CREATE TABLE asset (
  id            text PRIMARY KEY,
  plant_id      text NOT NULL,
  parent_id     text REFERENCES asset(id),
  kind          text NOT NULL,
  template_id   text NOT NULL REFERENCES asset_template(id),
  name          text NOT NULL,
  attrs         jsonb NOT NULL DEFAULT '{}'
);
"""

DOWNGRADE = """
DROP TABLE asset;
DROP TABLE asset_template;
DROP TABLE source_batch;
DROP TABLE dataset;
DROP TYPE wo_status;
DROP TYPE contract_kind;
DROP TYPE confidence;
DROP TYPE event_category;
DROP TYPE quality_flag;
DROP TYPE source_kind;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
