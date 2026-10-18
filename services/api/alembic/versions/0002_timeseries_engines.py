"""M1-M3 tables: docs/04 §3 time series, §4 events/ops, §5 baseline/contracts, §6 money engines; D11 and D15.

Revision ID: 0002_timeseries_engines
Revises: 0001_m0_core
Create Date: 2026-10-18
"""

from alembic import op

revision = "0002_timeseries_engines"
down_revision = "0001_m0_core"
branch_labels = None
depends_on = None

UPGRADE = """
CREATE TABLE measurement (
  dataset_id    text NOT NULL REFERENCES dataset(id),
  asset_id      text NOT NULL REFERENCES asset(id),
  quantity      text NOT NULL,
  ts_start      timestamptz NOT NULL,
  interval_s    int NOT NULL DEFAULT 900,
  value         double precision,
  value_text    text,
  unit          text NOT NULL,
  quality       quality_flag NOT NULL,
  source_kind   source_kind NOT NULL,
  batch_id      uuid NOT NULL REFERENCES source_batch(id),
  received_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (dataset_id, asset_id, quantity, ts_start)
);

CREATE TABLE expected_output (
  dataset_id    text NOT NULL REFERENCES dataset(id),
  asset_id      text NOT NULL REFERENCES asset(id),
  ts_start      timestamptz NOT NULL,
  interval_s    int NOT NULL,
  poa_wm2       double precision, t_cell_c double precision,
  e_potential_kwh double precision NOT NULL,
  band_rel      double precision NOT NULL,
  clipped       boolean NOT NULL,
  model_version text NOT NULL,
  inputs_hash   text NOT NULL,
  PRIMARY KEY (dataset_id, asset_id, ts_start, model_version)
);

CREATE TABLE actual_output (
  dataset_id    text NOT NULL, asset_id text NOT NULL, ts_start timestamptz NOT NULL,
  e_kwh         double precision,
  quality       quality_flag NOT NULL,
  status        text,
  PRIMARY KEY (dataset_id, asset_id, ts_start)
);

CREATE TABLE event (
  id            uuid PRIMARY KEY,
  dataset_id    text NOT NULL REFERENCES dataset(id),
  asset_id      text NOT NULL REFERENCES asset(id),
  category      event_category NOT NULL,
  cause_code    text NOT NULL,
  start_ts      timestamptz NOT NULL,
  end_ts        timestamptz,
  controllable  boolean NOT NULL,
  confidence    confidence NOT NULL,
  evidence      jsonb NOT NULL,
  setpoint_kw   double precision,
  source_kind   source_kind NOT NULL
);

CREATE TABLE work_order (
  id            uuid PRIMARY KEY,
  event_id      uuid NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  severity      text NOT NULL CHECK (severity IN ('critical','major','minor')),
  status        wo_status NOT NULL,
  opened_at timestamptz NOT NULL, acked_at timestamptz, onsite_at timestamptz,
  restored_at timestamptz, verified_at timestamptz,
  priority_score double precision, priority_inputs jsonb,
  source_kind   source_kind NOT NULL
);

-- D15: operator records (work-order lifecycle timestamps, cleaning log). docs/04 had no table for them.
CREATE TABLE operator_log (
  id            uuid PRIMARY KEY,
  dataset_id    text NOT NULL REFERENCES dataset(id),
  asset_id      text NOT NULL REFERENCES asset(id),
  kind          text NOT NULL CHECK (kind IN ('acknowledged','onsite','restored','verified','cleaning')),
  at            timestamptz NOT NULL,
  note          text,
  source_kind   source_kind NOT NULL
);
CREATE INDEX ON operator_log (dataset_id, asset_id, at);

CREATE TABLE baseline (
  id            uuid PRIMARY KEY,
  plant_id      text NOT NULL,
  version       int NOT NULL,
  status        text NOT NULL CHECK (status IN ('draft','approved')),
  valid_month   date NOT NULL,
  energy_p50_kwh numeric(16,1) NOT NULL,
  energy_p90_kwh numeric(16,1) NOT NULL,
  revenue_p50_inr numeric(18,2) NOT NULL,
  opex_inr       numeric(18,2) NOT NULL,
  tax_inr        numeric(18,2) NOT NULL,
  debt_service_inr numeric(18,2) NOT NULL,
  assumptions   jsonb NOT NULL,
  approved_at   timestamptz, approved_by text, reason text,
  supersedes    int,
  UNIQUE (plant_id, version, valid_month)
);
CREATE FUNCTION forbid_approved_baseline_change() RETURNS trigger AS $$
BEGIN
  IF OLD.status = 'approved' THEN RAISE EXCEPTION 'baseline v% is approved and immutable', OLD.version; END IF;
  RETURN COALESCE(NEW, OLD);
END $$ LANGUAGE plpgsql;
CREATE TRIGGER baseline_immutable BEFORE UPDATE OR DELETE ON baseline
  FOR EACH ROW EXECUTE FUNCTION forbid_approved_baseline_change();

CREATE TABLE contract (
  id            text PRIMARY KEY,
  kind          contract_kind NOT NULL,
  plant_id      text NOT NULL,
  version       int NOT NULL,
  effective_from date NOT NULL, effective_to date,
  terms         jsonb NOT NULL,
  sha256        text NOT NULL,
  source_kind   source_kind NOT NULL
);

CREATE TABLE accounting_ledger (
  dataset_id text NOT NULL, plant_id text NOT NULL, period_month date NOT NULL,
  meter_kwh double precision NOT NULL, inverter_sum_kwh double precision NOT NULL,
  export_loss_kwh double precision NOT NULL, accountable_kwh double precision NOT NULL,
  recon_delta_pct double precision NOT NULL, rule_refs jsonb NOT NULL,
  hours_with_generation double precision NOT NULL,
  backdown_hours double precision NOT NULL,
  grid_unavail_hours_counted double precision NOT NULL,
  PRIMARY KEY (dataset_id, plant_id, period_month)
);

CREATE TABLE settlement_line (
  id uuid PRIMARY KEY,
  dataset_id text NOT NULL, plant_id text NOT NULL,
  period_start date NOT NULL, period_kind text NOT NULL CHECK (period_kind IN ('month','year')),
  kind text NOT NULL CHECK (kind IN ('energy_charge','backdown_comp','grid_unavail_comp','excess_repricing','shortfall_comp')),
  qty_kwh numeric(16,1), rate_inr_per_kwh numeric(10,4), amount_inr numeric(18,2) NOT NULL,
  contract_id text NOT NULL REFERENCES contract(id), clause_ref text NOT NULL,
  inputs jsonb NOT NULL, provisional boolean NOT NULL
);

CREATE TABLE om_ld_line (
  id uuid PRIMARY KEY, dataset_id text NOT NULL, plant_id text NOT NULL, year int NOT NULL,
  availability_energy numeric(8,6) NOT NULL, ld_kwh numeric(16,1) NOT NULL,
  amount_inr numeric(18,2) NOT NULL, capped boolean NOT NULL,
  contract_id text NOT NULL REFERENCES contract(id), inputs jsonb NOT NULL, provisional boolean NOT NULL
);

CREATE TABLE finance_period (
  dataset_id text NOT NULL, plant_id text NOT NULL, period_month date NOT NULL,
  revenue_settled_inr numeric(18,2) NOT NULL, om_ld_inr numeric(18,2) NOT NULL,
  opex_inr numeric(18,2) NOT NULL, tax_inr numeric(18,2) NOT NULL, capex_inr numeric(18,2) NOT NULL,
  cfads_inr numeric(18,2) NOT NULL, debt_service_inr numeric(18,2) NOT NULL,
  dscr_ytd numeric(8,4), provisional boolean NOT NULL,
  PRIMARY KEY (dataset_id, plant_id, period_month)
);

CREATE TABLE audit_event (
  id uuid PRIMARY KEY, actor text NOT NULL, action text NOT NULL, object text NOT NULL,
  detail jsonb NOT NULL, at timestamptz NOT NULL DEFAULT now()
);
"""

DOWNGRADE = """
DROP TABLE audit_event;
DROP TABLE finance_period;
DROP TABLE om_ld_line;
DROP TABLE settlement_line;
DROP TABLE accounting_ledger;
DROP TABLE contract;
DROP TRIGGER baseline_immutable ON baseline;
DROP TABLE baseline;
DROP FUNCTION forbid_approved_baseline_change();
DROP TABLE operator_log;
DROP TABLE work_order;
DROP TABLE event;
DROP TABLE actual_output;
DROP TABLE expected_output;
DROP TABLE measurement;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
