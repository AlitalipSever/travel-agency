# Single entry point (docs/06-operations.md). Everything runs through docker compose unless
# the target says laptop.

COMPOSE := docker compose
API := $(COMPOSE) run --rm --no-deps api
API_DB := $(COMPOSE) run --rm api

.PHONY: help up down logs worker-logs refresh ps build migrate seed demo makemigrations test test-fast lint fmt shell superuser psql env

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

env:             ## create api/.env from .env.example when missing
	@test -f api/.env || cp .env.example api/.env

up: env          ## start postgres, redis, migrate, api (http://localhost:8000)
	$(COMPOSE) up --build -d
	@echo "api: http://localhost:8000/api/docs  admin: http://localhost:8000/admin/"

down:            ## stop everything, keep data
	$(COMPOSE) down

logs:            ## follow api logs
	$(COMPOSE) logs -f api

worker-logs:     ## follow worker and beat logs
	$(COMPOSE) logs -f worker beat

refresh:         ## run one weather refresh now (through the worker queue)
	$(API_DB) python manage.py shell -c "from weather.tasks import refresh_all; print('queued', refresh_all.delay('manual').id)"

ps:              ## running services
	$(COMPOSE) ps

build:           ## rebuild the api image
	$(COMPOSE) build api

migrate:         ## apply migrations
	$(API_DB) python manage.py migrate --noinput

seed:            ## insert the capitals and destination types that are missing (idempotent)
	$(API_DB) python manage.py seed_locations && $(API_DB) python manage.py seed_destination_types

demo: seed       ## demo partner, users with tokens, destinations, packages, departures, bookings
	$(API_DB) python manage.py seed_demo

makemigrations:  ## create migrations from model changes
	$(API_DB) python manage.py makemigrations

test:            ## full test suite inside the container (needs postgres from `make up`)
	$(API_DB) python -m pytest -q -p no:cacheprovider

test-fast:       ## laptop: tests that need no database
	cd api && uv run pytest -q -p no:cacheprovider -m "not django_db"

lint:            ## laptop: ruff and mypy
	cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy .

fmt:             ## laptop: format
	cd api && uv run ruff format .

shell:           ## Django shell in the container
	$(API_DB) python manage.py shell

superuser:       ## create an admin user (ops) interactively
	$(API_DB) python manage.py createsuperuser

psql:            ## psql into the compose database
	$(COMPOSE) exec postgres psql -U travel -d travel
