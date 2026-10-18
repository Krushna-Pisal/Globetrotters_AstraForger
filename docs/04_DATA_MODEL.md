# 04 — Data Model (PostgreSQL 16)

One store, one schema. Every view is a query over `metric_value` (plus event lists the lens allows).
Implement with SQLAlchemy 2 models + Alembic migrations that match this DDL. Names are binding; add columns only
through a migration and a note in `docs/10_DECISIONS.md`.

## 1. Enumerations
```sql
CREATE TYPE source_kind AS ENUM ('measured','weather_estimated','modeled','synthetic_scenario',
  'synthetic_reference','synthetic_contract','derived','operator');
CREATE TYPE quality_flag AS ENUM ('ok','estimated','no_data','suspect');
CREATE TYPE event_category AS ENUM ('equipment_outage','grid_unavailability','curtailment','comms_loss',
  'underperformance','cleaning','other');
CREATE TYPE confidence AS ENUM ('confirmed','suspected');
CREATE TYPE contract_kind AS ENUM ('ppa','om','loan');
CREATE TYPE wo_status AS ENUM ('open','acknowledged','onsite','restored','verified');
```

## 2. Identity, twin, provenance
```sql
CREATE TABLE dataset (
  id            text PRIMARY KEY,               -- 'kaggle_p2_2020', 'thar1_demo_2024'
  plant_id      text NOT NULL,
  kind          text NOT NULL CHECK (kind IN ('measured','synthetic')),
  seed          bigint,                         -- synthetic only
  config        jsonb NOT NULL,                 -- scenario yaml or source manifest
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_batch (
  id            uuid PRIMARY KEY,
  dataset_id    text NOT NULL REFERENCES dataset(id),
  source_name   text NOT NULL,                  -- 'kaggle:Plant_2_Generation_Data.csv', 'open_meteo_archive'
  url           text, license text,
  sha256        text NOT NULL,
  retrieved_at  timestamptz NOT NULL,
  source_kind   source_kind NOT NULL,
  notes         text
);

CREATE TABLE asset_template (id text PRIMARY KEY, kind text NOT NULL, schema jsonb NOT NULL);

CREATE TABLE asset (
  id            text PRIMARY KEY,               -- 'THAR1', 'THAR1/B2/INV-07', 'THAR1/MTR-DP'
  plant_id      text NOT NULL,
  parent_id     text REFERENCES asset(id),
  kind          text NOT NULL,                  -- plant|block|inverter|meter|weather_station
  template_id   text NOT NULL REFERENCES asset_template(id),
  name          text NOT NULL,
  attrs         jsonb NOT NULL DEFAULT '{}'     -- nameplate: dc_kwp, ac_kw, lat, lon, tilt ...
);
```

## 3. Time series
```sql
CREATE TABLE measurement (
  dataset_id    text NOT NULL REFERENCES dataset(id),
  asset_id      text NOT NULL REFERENCES asset(id),
  quantity      text NOT NULL,                  -- ac_power_kw, dc_power_kw, poa_wm2, ghi_wm2, t_mod_c, t_amb_c,
                                                -- wind_ms, precip_mm, status, setpoint_kw, heartbeat, energy_export_kwh
  ts_start      timestamptz NOT NULL,
  interval_s    int NOT NULL DEFAULT 900,
  value         double precision,               -- NULL allowed when no_data
  value_text    text,                           -- status codes
  unit          text NOT NULL,
  quality       quality_flag NOT NULL,
  source_kind   source_kind NOT NULL,
  batch_id      uuid NOT NULL REFERENCES source_batch(id),
  received_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (dataset_id, asset_id, quantity, ts_start)   -- idempotent upsert key
);

CREATE TABLE expected_output (
  dataset_id    text NOT NULL REFERENCES dataset(id),
  asset_id      text NOT NULL REFERENCES asset(id),
  ts_start      timestamptz NOT NULL,
  interval_s    int NOT NULL,
  poa_wm2       double precision, t_cell_c double precision,
  e_potential_kwh double precision NOT NULL,
  band_rel      double precision NOT NULL,      -- 1.96 σ_rel
  clipped       boolean NOT NULL,
  model_version text NOT NULL,
  inputs_hash   text NOT NULL,
  PRIMARY KEY (dataset_id, asset_id, ts_start, model_version)
);

CREATE TABLE actual_output (                    -- validated inverter AC energy
  dataset_id    text NOT NULL, asset_id text NOT NULL, ts_start timestamptz NOT NULL,
  e_kwh         double precision,
  quality       quality_flag NOT NULL,
  status        text,
  PRIMARY KEY (dataset_id, asset_id, ts_start)
);
```

## 4. Events and operations
```sql
CREATE TABLE event (
  id            uuid PRIMARY KEY,
  dataset_id    text NOT NULL REFERENCES dataset(id),
  asset_id      text NOT NULL REFERENCES asset(id),
  category      event_category NOT NULL,
  cause_code    text NOT NULL,
  start_ts      timestamptz NOT NULL,
  end_ts        timestamptz,                    -- NULL = ongoing
  controllable  boolean NOT NULL,
  confidence    confidence NOT NULL,
  evidence      jsonb NOT NULL,                 -- {rules:[...], metrics:{...}}
  setpoint_kw   double precision,
  source_kind   source_kind NOT NULL            -- 'derived' for detected events
);

CREATE TABLE work_order (
  id            uuid PRIMARY KEY,
  event_id      uuid NOT NULL REFERENCES event(id),
  severity      text NOT NULL CHECK (severity IN ('critical','major','minor')),
  status        wo_status NOT NULL,
  opened_at timestamptz NOT NULL, acked_at timestamptz, onsite_at timestamptz,
  restored_at timestamptz, verified_at timestamptz,
  priority_score double precision, priority_inputs jsonb,
  source_kind   source_kind NOT NULL            -- 'operator' (real) or 'synthetic_scenario'
);
```

## 5. Baseline, contracts (immutable)
```sql
CREATE TABLE baseline (
  id            uuid PRIMARY KEY,
  plant_id      text NOT NULL,
  version       int NOT NULL,
  status        text NOT NULL CHECK (status IN ('draft','approved')),
  valid_month   date NOT NULL,                  -- first day of month described
  energy_p50_kwh numeric(16,1) NOT NULL,
  energy_p90_kwh numeric(16,1) NOT NULL,
  revenue_p50_inr numeric(18,2) NOT NULL,
  opex_inr       numeric(18,2) NOT NULL,
  tax_inr        numeric(18,2) NOT NULL,
  debt_service_inr numeric(18,2) NOT NULL,
  assumptions   jsonb NOT NULL,                 -- loss register, sigma, weather basis, model_version
  approved_at   timestamptz, approved_by text, reason text,
  supersedes    int,
  UNIQUE (plant_id, version, valid_month)
);
-- Immutability: block UPDATE/DELETE of approved rows
CREATE FUNCTION forbid_approved_baseline_change() RETURNS trigger AS $$
BEGIN
  IF OLD.status = 'approved' THEN RAISE EXCEPTION 'baseline v% is approved and immutable', OLD.version; END IF;
  RETURN COALESCE(NEW, OLD);
END $$ LANGUAGE plpgsql;
CREATE TRIGGER baseline_immutable BEFORE UPDATE OR DELETE ON baseline
  FOR EACH ROW EXECUTE FUNCTION forbid_approved_baseline_change();

CREATE TABLE contract (
  id            text PRIMARY KEY,               -- 'PPA-THAR1-v1'
  kind          contract_kind NOT NULL,
  plant_id      text NOT NULL,
  version       int NOT NULL,
  effective_from date NOT NULL, effective_to date,
  terms         jsonb NOT NULL,                 -- parsed YAML
  sha256        text NOT NULL,
  source_kind   source_kind NOT NULL
);
```

## 6. Money engines (separate tables by counterparty)
```sql
CREATE TABLE accounting_ledger (
  dataset_id text NOT NULL, plant_id text NOT NULL, period_month date NOT NULL,
  meter_kwh double precision NOT NULL, inverter_sum_kwh double precision NOT NULL,
  export_loss_kwh double precision NOT NULL, accountable_kwh double precision NOT NULL,
  recon_delta_pct double precision NOT NULL, rule_refs jsonb NOT NULL,
  -- D11: settlement may read only accounting, so the delivery-point ledger carries the hour counts the PPA clauses need
  hours_with_generation double precision NOT NULL,   -- hours with accountable export > 0 (C4.4/C4.5 avg_gen_per_hour)
  backdown_hours double precision NOT NULL,          -- hours with an SLDC backdown instruction (C4.4)
  grid_unavail_hours_counted double precision NOT NULL, -- plant OFFLINE hours inside 08:00–18:00 local (C4.5)
  PRIMARY KEY (dataset_id, plant_id, period_month)
);

CREATE TABLE settlement_line (                 -- PPA only (generator ↔ offtaker)
  id uuid PRIMARY KEY,
  dataset_id text NOT NULL, plant_id text NOT NULL,
  period_start date NOT NULL, period_kind text NOT NULL CHECK (period_kind IN ('month','year')),
  kind text NOT NULL CHECK (kind IN ('energy_charge','backdown_comp','grid_unavail_comp','excess_repricing','shortfall_comp')),
  qty_kwh numeric(16,1), rate_inr_per_kwh numeric(10,4), amount_inr numeric(18,2) NOT NULL,
  contract_id text NOT NULL REFERENCES contract(id), clause_ref text NOT NULL,
  inputs jsonb NOT NULL, provisional boolean NOT NULL
);

CREATE TABLE om_ld_line (                      -- O&M contract (contractor → owner)
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
```

## 7. Explanation and registry
```sql
CREATE TABLE attribution_step (
  dataset_id text NOT NULL, plant_id text NOT NULL, period_start date NOT NULL, period_kind text NOT NULL,
  bridge text NOT NULL CHECK (bridge IN ('energy','revenue','liability')),
  step_order int NOT NULL, bucket text NOT NULL, bearer text,
  value numeric(18,2) NOT NULL, unit text NOT NULL,
  controllable boolean, confidence confidence, evidence jsonb NOT NULL,
  PRIMARY KEY (dataset_id, plant_id, period_start, period_kind, bridge, step_order, bucket, bearer)
);

CREATE TABLE metric_definition (
  id text NOT NULL, version int NOT NULL, label text NOT NULL, unit text NOT NULL,
  grain jsonb NOT NULL, rollup text NOT NULL, ref text NOT NULL, layer jsonb, questions jsonb,
  PRIMARY KEY (id, version)
);

CREATE TABLE metric_value (
  id uuid PRIMARY KEY,
  metric_id text NOT NULL, metric_version int NOT NULL,
  dataset_id text NOT NULL, asset_id text NOT NULL,
  period_start timestamptz NOT NULL, period_grain text NOT NULL,   -- interval_15m|day|month|year|ytd
  dims jsonb NOT NULL DEFAULT '{}',                                 -- {cause_bucket:'soiling', bearer:'owner', bridge_step:'C'}
  value numeric NOT NULL, unit text NOT NULL,
  source_kind source_kind NOT NULL, quality quality_flag NOT NULL, provisional boolean NOT NULL DEFAULT false,
  lineage jsonb NOT NULL,           -- {inputs:[{table, keys}], formula_ref, contract_id?, model_version?, baseline_version?}
  lineage_hash text NOT NULL,       -- sha256 of canonical JSON of (metric_id, version, dims, inputs, value)
  UNIQUE (metric_id, metric_version, dataset_id, asset_id, period_start, period_grain, dims)
);
CREATE INDEX ON metric_value (dataset_id, metric_id, period_grain, period_start);

CREATE TABLE recon_result (
  run_id uuid NOT NULL, test_id text NOT NULL, dataset_id text NOT NULL, period_start date,
  passed boolean NOT NULL, detail jsonb NOT NULL, ran_at timestamptz NOT NULL,
  PRIMARY KEY (run_id, test_id, dataset_id, period_start)
);

CREATE TABLE audit_event (
  id uuid PRIMARY KEY, actor text NOT NULL, action text NOT NULL, object text NOT NULL,
  detail jsonb NOT NULL, at timestamptz NOT NULL DEFAULT now()
);
```

## 8. Rules the schema enforces or the tests must enforce
- `measurement` upsert on PK → re-ingest never duplicates.
- Approved `baseline` rows cannot change (trigger) — test asserts the exception.
- `settlement_line.kind` has no O&M kinds; `om_ld_line` is separate — test asserts no LD money in settlement totals.
- `metric_value.lineage_hash` identical across lenses for the same row — lenses read rows, they never recompute.
- Synthetic rows only in datasets with `dataset.kind = 'synthetic'` — test asserts no `synthetic_*` source_kind in a measured dataset and vice versa.
