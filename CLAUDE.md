# CLAUDE.md — PS4 Performance Assurance Platform ("One Asset, Three Truths")

You are the implementation engineer for this repo. Read this file fully at the start of every session.

## What we are building (one paragraph)
One canonical model of a solar plant (design → expected → actual → accounted → settled → financed → explained),
one metric registry where every number is defined once with lineage, and three **server-enforced** lens
contracts that project that single source for an **Engineer**, an **Operations manager** and a **CFO**.
Each view states what it deliberately leaves out and why. The demo is one inverter outage told three ways,
plus a recurrence that escalates into the CFO view. Correct domain model first, polish second.

## Source-of-truth order (when documents disagree)
1. `docs/02_DOMAIN_REFERENCE.md` — formulas, contract mechanics, attribution algorithm (authoritative for numbers)
2. `docs/04_DATA_MODEL.md` and `docs/05_API_CONTRACT.md` — schema and payload shapes
3. `configs/**` — parameters (plant, baseline, contracts, lenses, metrics, scenario)
4. `docs/07_MVP_PLAN.md` — what to build now, milestone by milestone
5. Everything else is context. If two sources conflict, STOP and ask; do not pick silently.

## Non-negotiable invariants (tests exist or must exist for each)
1. **Baseline is frozen.** Approved baseline rows are never updated or deleted (DB trigger + test). A revision is a new version.
2. **Settlement never reads the baseline.** `app.settlement` may import only `app.accounting`, `app.contracts` (PPA loader), `app.core`. Enforced by import-linter in CI.
3. **Two contracts, two cash flows.** PPA settlement (generator ↔ offtaker) and O&M liquidated damages (contractor ↔ owner) are computed by different modules and stored in different tables. Never put O&M LDs in PPA settlement.
4. **Every lost kWh lands somewhere.** Each energy gap is assigned to exactly one named bucket or the explicit residual. Bridges close to the kWh / to the paisa.
5. **Attribution is variance against the baseline's own assumptions.** The baseline already assumes some soiling and availability loss; buckets report actual − assumed, never the gross loss.
6. **No screen computes.** The web app renders only values from the registry via lens endpoints. No arithmetic on metrics in React beyond formatting.
7. **Lenses are enforced on the server.** A role's response contains only allowlisted fields. Forbidden metric ids must not appear anywhere in the JSON (test greps the payload). Hidden-by-CSS is a bug.
8. **Provenance on every record:** `source_kind` ∈ {measured, weather_estimated, modeled, synthetic_scenario, synthetic_reference, synthetic_contract, derived, operator}. Synthetic and measured data never share a `dataset_id`.
9. **Never fabricate measured data.** Synthetic data comes only from `configs/scenarios/*.yaml` through the scenario generator, with a seed, and is labelled. Never invent dataset columns.
10. **No public AI APIs at runtime.** Any model runs locally (Ollama). No LLM computes any metric.
11. **Ops is judged against weather-adjusted expected output, never the baseline.**
12. **Monitoring only.** No code path writes commands to equipment or to a source system.

## Stack
- Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, PostgreSQL 16, pvlib, pandas, numpy, pytest, import-linter, ruff.
- Frontend: **React + TypeScript + Vite only** (no Next.js — Quest rule "React only"), TanStack Query, ECharts (`echarts-for-react`), Tailwind.
- Infra: Docker Compose (db + api + web). Everything must run offline after `make fetch-weather` has cached weather once.

## Repo layout
```
apps/web/                         React app (pages: engineer, operations, cfo, rosetta, scorecard, baseline)
services/api/app/
  core/          config, db session, auth (demo JWT), units, money (Decimal), lineage hashing
  ingest/        source manifests, kaggle + weather adapters
  quality/       validation flags, data-quality score
  twin/          plant + asset templates, hierarchy
  performance/   pvlib model → expected_output with uncertainty band
  scenarios/     synthetic year generator + ground_truth
  detection/     status / peer / expected-shortfall rules → events
  accounting/    delivery-point ledger (accountable kWh)
  contracts/     loaders + validators for ppa, om, loan YAML
  settlement/    PPA settlement ONLY
  om/            energy availability, LDs, SLA, work orders
  finance/       CFADS, DSCR
  baseline/      TMY P50/P90 build, freeze, versions
  attribution/   energy bridge, revenue bridge, liability map
  metrics/       registry, compute, lineage
  reconciliation/ closure checks exposed as results
  lenses/        lens specs, projection, materiality, escalation
  api/           routers
services/api/pipelines/run.py     CLI orchestrating the steps
services/api/tests/{unit,integration,reconciliation,security,scorecard}
configs/                           plant, baseline, contracts, lenses, metrics, scenarios
data/{raw,manifests,processed,fixtures}
docs/
```

## Commands (create them in M0; keep this list current)
```
make up               # docker compose up db api web
make migrate          # alembic upgrade head
make fetch-weather    # download + cache weather/TMY to data/raw (only step needing internet)
make ingest-kaggle    # load Kaggle Plant 2 real slice (dataset kaggle_p2_2020)
make baseline         # build baseline v1 draft from TMY; make approve-baseline freezes it
make scenario         # generate synthetic year thar1_demo_2024 + ground_truth.json
make pipeline DATASET=thar1_demo_2024   # quality → expected → detect → accounting → settlement → om → finance → attribution → metrics → reconcile
make test             # pytest (all) ; make recon = reconciliation suite only
make lint             # ruff + import-linter + tsc
make demo             # reset db, seed everything, start app
```

## How to work in this repo
- One milestone per session (see `docs/07_MVP_PLAN.md`). Read that milestone's section and the docs it cites before editing.
- Inspect existing files first; extend, don't rewrite. List the files you will touch before you touch them.
- Engines are test-first: write the closure/consistency test, then the code.
- Money: `decimal.Decimal`, quantize to paise (0.01) per line with ROUND_HALF_UP, then sum lines. Never float for INR.
- Energy: store kWh as float64 in time series; aggregate in kWh; display MWh/GWh only in the web layer formatter.
- Time: store UTC (`timestamptz`), interval-start convention, 15-min intervals. Plant display tz Asia/Kolkata (UTC+05:30, no DST).
- Every engine output row carries `dataset_id`, `source_kind`, `model_version` or `contract_id`, and a lineage reference.
- End every milestone with: changed files list, commands run, test results, known limitations, next prerequisites.

## Known gotchas (read before touching weather or data code)
- **Azimuth conventions differ.** pvlib: 180° = south. Open-Meteo GTI and PVGIS `aspect`: 0° = south. Convert explicitly.
- **Open-Meteo radiation is the mean of the preceding hour**, stamped at hour end. Compute solar position at the interval midpoint (t − 30 min).
- **NASA POWER hourly**: confirm the time-standard option (UTC vs local solar time) before use; store UTC.
- **Kaggle Plant 1 DC_POWER is ~10× AC_POWER** (reported AC/DC ≈ 9.8%) — do not use Plant 1 DC. Plant 2 is ≈ 97.8% and is our real slice.
- **Kaggle date formats differ between files.** Parse each file with an explicit format and assert a monotonic 15-min index.
- **Kaggle IRRADIATION units**: check the max. If it is ≈ 1.0–1.3, it is kW/m² → multiply by 1000.
- **Kaggle DAILY_YIELD/TOTAL_YIELD are cumulative.** Never sum them as power. Energy per interval = AC_POWER(kW) × 0.25 h; cross-check against ΔDAILY_YIELD.
- **CUF is on contracted AC capacity** (50,000 kW for THAR1), annual, 8,760 h (8,784 in 2024: use actual hours of the contract year).
- A zero can be a fault, a curtailment, or missing data. Status + heartbeat decide; never treat all zeros as outages.

## Definition of done (every milestone)
Tests green (`make test`, `make lint`), invariants untouched, README section updated, demo still runs from `make demo`,
no unlabelled synthetic data, no TODO left in engine math.
