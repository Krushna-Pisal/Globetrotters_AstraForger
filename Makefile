# All targets run inside Docker containers (D14), so they behave the same on Windows, macOS and Linux.
# Recipes avoid shell-specific syntax so GNU make works with either cmd.exe or sh.

DATASET ?= thar1_demo_2024
COMPOSE := docker compose
API := $(COMPOSE) exec -T api
WEB := $(COMPOSE) exec -T web
RUN := $(API) python -m pipelines.run

.PHONY: up down migrate fetch-weather ingest-kaggle baseline approve-baseline scenario pipeline test recon lint demo

up:
	$(COMPOSE) up -d --build --wait db api web

down:
	$(COMPOSE) down

migrate:
	$(API) alembic upgrade head

fetch-weather:
	$(RUN) --command fetch-weather

ingest-kaggle:
	$(RUN) --command ingest-kaggle

baseline:
	$(RUN) --command baseline

approve-baseline:
	$(RUN) --command approve-baseline

scenario:
	$(RUN) --command scenario

pipeline:
	$(RUN) --dataset $(DATASET) --steps all

test:
	$(API) pytest

recon:
	$(API) pytest tests/reconciliation

lint:
	$(API) ruff check .
	$(API) ruff format --check .
	$(API) lint-imports
	$(WEB) npm run typecheck

# M0: reset the database and start the stack. Seeding steps are added as their milestones land.
demo:
	$(COMPOSE) down -v
	$(MAKE) up
	$(MAKE) migrate
