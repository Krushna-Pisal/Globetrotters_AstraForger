# One Asset, Three Truths — PS4 Performance Assurance Platform

One canonical model of a solar plant, one metric registry, and three server-enforced lenses (Engineer, Operations, CFO).
Start with [`CLAUDE.md`](CLAUDE.md) and [`docs/00_INDEX.md`](docs/00_INDEX.md).

## Prerequisites
- Docker Desktop (Compose v2.24+)
- GNU make — on Windows: `winget install ezwinports.make`
- Internet only for `make fetch-weather` (once); everything else runs offline.

Every make target runs inside the containers, so no local Python or PostgreSQL is needed.

## Quick start
```
make up        # build and start db (postgres 16), api (FastAPI :8000), web (Vite :5173); waits until healthy
make migrate   # alembic upgrade head
make test      # pytest (uses a separate ps4_test database, recreated each run)
make lint      # ruff check + ruff format --check + import-linter + tsc
make recon     # reconciliation suite only
```
Open http://localhost:5173 (web) and http://localhost:8000/docs (API).

Demo login: `POST /v1/auth/demo-login {"user": "engineer" | "operations" | "cfo" | "presenter"}` → bearer token.
The role is read only from the token.

## Status by milestone (docs/07)
| Milestone | State |
|---|---|
| M0 Bootstrap | Done: layout, compose, `/health`, demo JWT login, import-linter contracts, CI |
| M1 Real slice | Done: Kaggle Plant 2 ingest (`kaggle_p2_2020`), quality flags + score, real-data expected model, peer detection, texture calibration |
| M2 Synthetic year | Done: twin, Open-Meteo/NASA POWER adapters, 15-min downscaling, pvlib chain + band, scenario generator + ground truth, status/peer detection |
| M3 Money engines | Done: PVGIS baseline v1 (frozen), contract loaders, accounting ledger, PPA settlement, A_E + LDs + work orders, CFADS/DSCR, baseline API |
| Prototype UI | Done: password login, Plant overview, Engineering, Operations, Finance and Baseline pages on real engine data, role-enforced on the server (D30–D32) |
| M4–M7 | Paused. M4 work in progress is parked on branch `wip/m4-attribution`; `make pipeline` lists the pending steps |

## Prototype UI
Open http://localhost:5173 after `make demo` (or `make up && make migrate && make seed-users` on an existing database).

| Account | Password | Lands on | Sees |
|---|---|---|---|
| `engineer` | `thar1-engineer` | Engineering | kWh vs expected, PR₂₅ trend, inverter × day heatmap, loss waterfall, events with 15-min traces |
| `operations` | `thar1-operations` | Operations | availability vs 99 % guarantee, ranked work queue with SLA clocks and transitions, cleaning compliance, curtailment log |
| `cfo` | `thar1-cfo` | Finance | revenue and energy vs P50/P90, DSCR vs covenants, escalations (materiality / recurrence / covenant), settlement lines, CFADS |
| `presenter` | `thar1-presenter` | Plant overview | every view, plus the month-by-month "three truths" matrix |

Each view ends with an "Out of scope" panel and a "Server stripped N items" receipt; the API refuses to send anything
outside the role's lens (`configs/lenses/*.yaml`). Demo passwords are for local demos only — set `DEMO_PASSWORD_*` in `.env`.

Suggested demo path: sign in as `presenter` → overview matrix → April on Engineering (INV-07 outage trace) →
Operations (same event as a work order, SLA met) → Finance in April (event absent, below materiality) → July
(IGBT_OVERTEMP escalates as a structural issue) → May on Operations (the missed 4 May cleaning).

## Seeding the data
```
make fetch-weather     # once, needs internet: Open-Meteo 2024 + PVGIS TMY -> data/raw/weather (cached)
make ingest-kaggle     # needs data/raw/kaggle/*.csv (download from Kaggle yourself, see docs/06)
make scenario          # synthetic year thar1_demo_2024 + data/processed/thar1_demo_2024/ground_truth.json
make baseline          # baseline v1 draft from the TMY; make approve-baseline freezes it (writes declared CUF)
make pipeline DATASET=thar1_demo_2024   # quality -> expected -> detect -> accounting -> settlement -> om -> finance
make seed-users        # demo login accounts
make demo              # all of the above from a clean database, offline once weather is cached (~10 min)
```

### What the engines produce today (seed 20241017)
| | Result |
|---|---|
| Kaggle Plant 2 | 22 inverters, irradiance in kW/m² (×1000), AC/DC 0.978 (Plant 1: 0.098 → not used); σ_rel 0.086; holdout median daily APE 7.6 %; 16 inverters with real midday drop-outs flagged *suspected* |
| Detection on THAR1 | All 7 outages (E01–E07) found with exact start/end, 3 grid events, 10 curtailment windows, INV-17 silent derate from 2024-09-01, no false positives; E10 comms loss = 16 `no_data` intervals, no event |
| Baseline v1 | PVGIS-ERA5 TMY: P50 117.75 GWh, P90 107.94 GWh, ₹29.44 cr; declared CUF 26.9 % (D24) |
| 2024 actual | Accountable 105.55 GWh; settlement ₹26.39 cr energy + ₹12.37 lakh backdown (40 h); grid 14 h < 175.2 h → ₹0; no shortfall (deemed hours relax the minimum) |
| O&M / finance | A_E 99.81 % ≥ 99.0 % → no LD; 9 work orders, 3 SLA breaches (E05 at 110 h, INV-17 open); DSCR_YTD 1.32x |

Known limitations: attribution, the metric registry and the full lens/lineage API are M4–M5; the Kaggle licence text is
unverified (manifest says so); 2024 weather is ~11 % below the TMY, so the CFO view will be weather-dominated.

## Layout
```
apps/web/                 React + TypeScript + Vite (pages are placeholders until M6)
services/api/app/         engines, one package per module (see CLAUDE.md); import-linter rules in services/api/.importlinter
services/api/alembic/     migrations (DDL mirrors docs/04)
services/api/pipelines/   pipeline CLI
services/api/tests/       unit, integration, reconciliation, security, scorecard
configs/                  plant, baseline, contracts, lenses, metrics, scenarios
data/                     raw (gitignored), manifests, processed (gitignored), fixtures
```
