# 03 — Architecture

## 1. Shape
```
 data/raw (immutable files + manifests)        configs/ (plant, baseline, contracts, lenses, metrics, scenarios)
        │                                               │
        ▼                                               ▼
 ┌──────────────── pipeline (services/api/pipelines/run.py, deterministic, per dataset) ───────────────┐
 │ ingest → quality → twin → performance(expected + band) → [scenario generator: synthetic only]      │
 │   → detection(events, work orders) → accounting → settlement(PPA) → om(availability, LD, SLA)      │
 │   → finance(CFADS, DSCR) → attribution(energy, revenue, liability) → metrics(registry, lineage)    │
 │   → reconciliation(results)                                                                         │
 └─────────────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                               ▼
                              PostgreSQL (docs/04) — metric_value is the only thing views read
                                               ▼
                       FastAPI: lens projection (server-side allowlist, materiality, escalation)
                                               ▼
                 React (Vite): Engineer · Operations · CFO · Rosetta · Scorecard · Baseline history
```
The baseline is built by a separate command from TMY weather (`make baseline`) and frozen by `make approve-baseline`.

## 2. Module boundaries (import-linter contracts — CI fails on violation)
```ini
[importlinter]
root_package = app

[importlinter:contract:settlement-firewall]
name = Settlement reads only accounting, contracts and core (D12)
type = forbidden
source_modules = app.settlement
forbidden_modules = app.baseline, app.attribution, app.finance, app.lenses, app.om, app.performance,
  app.detection, app.quality, app.twin, app.ingest, app.scenarios, app.metrics, app.reconciliation, app.api

[importlinter:contract:om-separate]
name = O&M engine does not import PPA settlement
type = forbidden
source_modules = app.om
forbidden_modules = app.settlement, app.baseline

[importlinter:contract:lenses-read-registry-only]
name = Lenses only read the registry
type = forbidden
source_modules = app.lenses
forbidden_modules = app.performance, app.settlement, app.attribution, app.finance, app.om, app.accounting

[importlinter:contract:engines-never-read-ground-truth]
name = Engines never read the scenario ground truth
type = forbidden
source_modules = app.detection, app.attribution, app.performance, app.quality
forbidden_modules = app.scenarios
```
`app.contracts` exposes `load_ppa()`, `load_om()`, `load_loan()` as separate functions so each engine can only ask for its own contract.

## 3. Pipeline orchestration
`python -m pipelines.run --dataset thar1_demo_2024 --steps all|<step,...> --from 2024-01 --to 2024-12`
- Each step is a pure function `(dataset_id, period) → rows`, idempotent (delete-and-insert per dataset/period/version inside one transaction, never touching `baseline` or `measurement`).
- Each step writes an `audit_event` with input hashes and row counts.
- Re-running the full pipeline on the same inputs yields identical `lineage_hash` values (test).

## 4. API layer
- Auth: demo JWT (HS256, secret from env) with claims `{sub, role, plants:[...]}`. Roles: `engineer`, `operations`, `cfo`, `presenter`.
  `presenter` may call `/rosetta` and `/scorecard`; it receives the **exact** payloads the three lenses produce (with their hashes).
- The role comes **only** from the token. The role switcher in the UI swaps tokens (three demo users), it never adds a query parameter.
- Lens projection: `lens_spec (YAML) × metric_value rows → LensPayload`. Pydantic response models use `extra="forbid"`; a final
  guard walks the serialised JSON and rejects any key or metric id outside the lens allowlist (500 + audit, never a leak).

## 5. Frontend
- Pages: `/engineer`, `/operations`, `/cfo`, `/rosetta/:eventId`, `/scorecard`, `/baseline`.
- Shared components: `MetricCard` (value, unit, provenance badge, provisional badge, reconciliation chip),
  `Waterfall` (ECharts custom series; residual hatched; step order labelled), `OmissionsPanel` (renders `omitted[]` reasons),
  `LineageDrawer` (calls `/lineage/{id}`), `RoleSwitcher` (token swap, keeps plant/period/event in URL),
  `ModeBadge` (`SYNTHETIC SCENARIO · thar1_demo_2024` / `MEASURED · kaggle_p2_2020` / `REPLAY 60×`), `DebugStrip` (stripped-field receipt).
- No arithmetic on metric values in React except formatting (kWh→MWh/GWh, ₹→lakh/crore).
- Design tokens shared by all pages; archetypes: CFO strategic, Ops operational, Engineer analytical (docs/01 §4).

## 6. Optional layers (stretch, not MVP)
- **Replay / live mode:** a replay service emits stored telemetry on a virtual clock (1×–60×) over WebSocket; same pipeline steps run incrementally; mode badge always visible.
- **SCADA simulator:** Modbus TCP server (`pymodbus`) exposing per-inverter registers fed by the replay service; read-only connector polls it into `measurement` with `source_kind` unchanged (`synthetic_scenario`) and `quantity` tags from a tag map. Monitoring only — the connector has no write path.
- **Local narrative:** Ollama model turns a lens payload into 3 sentences in that role's language; numbers are injected from the payload, the prompt forbids new numbers, and a check rejects any number not present in the payload.
