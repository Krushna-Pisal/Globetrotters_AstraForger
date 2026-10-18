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
```
Open http://localhost:5173 (web) and http://localhost:8000/docs (API).

Demo login: `POST /v1/auth/demo-login {"user": "engineer" | "operations" | "cfo" | "presenter"}` → bearer token.
The role is read only from the token.

## Status by milestone (docs/07)
| Milestone | State |
|---|---|
| M0 Bootstrap | Done: layout, compose, `/health`, demo JWT login, enums and identity/twin tables, import-linter contracts, CI |
| M1–M7 | Not started. Their make targets exist and exit with code 2, naming the milestone that implements them |

Make targets that are still stubs: `fetch-weather` (M2), `ingest-kaggle` (M1), `baseline`, `approve-baseline` (M3),
`scenario` (M2), `pipeline` (M2–M4). `make demo` currently resets the database, starts the stack and migrates.

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
