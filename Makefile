# Single entry point (docs/06-operations.md). Everything runs through docker compose unless
# the target says laptop.

COMPOSE := docker compose
API := $(COMPOSE) run --rm --no-deps api
API_DB := $(COMPOSE) run --rm api

.PHONY: help up down logs worker-logs refresh ps build migrate seed demo makemigrations test test-fast lint fmt shell superuser psql env web-dev web-build web-lint infra-plan infra-apply bootstrap hello-up hello-down images-push secrets secrets-check deploy

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

web-dev:         ## run the site with hot reload on http://localhost:3000 (needs pnpm)
	cd web && pnpm install && pnpm dev

web-build:       ## production build of the site
	cd web && pnpm install && pnpm build

web-lint:        ## eslint + type check of the site
	cd web && pnpm lint && pnpm exec next typegen && pnpm exec tsc --noEmit

# Platform (docs/06-operations.md §1, §2). Laptop targets; KUBECONFIG must point at the cluster.
KUBECONFIG ?= $(HOME)/.kube/travel-agency.yaml
export KUBECONFIG

infra-plan:      ## terraform plan for the Hetzner server (needs infra/terraform/.env)
	cd infra/terraform && set -a && . ./.env && set +a && terraform init -input=false >/dev/null && terraform plan -input=false

infra-apply:     ## terraform apply (asks for confirmation)
	cd infra/terraform && set -a && . ./.env && set +a && terraform apply -input=false

bootstrap:       ## ingress-nginx, cert-manager and the Let's Encrypt issuers on the cluster (idempotent)
	helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null
	helm repo add jetstack https://charts.jetstack.io >/dev/null
	helm repo update >/dev/null
	helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace -f infra/k8s/ingress-nginx.values.yaml --wait
	helm upgrade --install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace -f infra/k8s/cert-manager.values.yaml --wait
	kubectl apply -f infra/k8s/cluster-issuers.yaml
	kubectl get clusterissuer

hello-up:        ## temporary hello page on the public host (proves DNS, ingress, certificate)
	kubectl apply -f infra/k8s/hello/hello.yaml
	kubectl get certificate -n default

hello-down:      ## remove the hello page (the application chart takes over the host)
	kubectl delete -f infra/k8s/hello/hello.yaml --ignore-not-found

# Images from an arm64 laptop (Apple Silicon builds natively; CI builds the same tags on main).
REGISTRY ?= ghcr.io/alitalipsever
TAG ?= $(shell git rev-parse HEAD)
PLATFORMS ?= linux/arm64

images-push:     ## build api and web images for the server and push them to ghcr (needs docker login ghcr.io)
	docker buildx build --platform $(PLATFORMS) --build-arg GIT_COMMIT=$(TAG) -t $(REGISTRY)/travel-agency-api:$(TAG) -t $(REGISTRY)/travel-agency-api:latest --push api
	docker buildx build --platform $(PLATFORMS) -f web/Dockerfile -t $(REGISTRY)/travel-agency-web:$(TAG) -t $(REGISTRY)/travel-agency-web:latest --push .
	@echo "pushed $(REGISTRY)/travel-agency-{api,web}:$(TAG)"

NAMESPACE ?= travel-agency
VALUES ?= chart/values-hetzner.yaml

secrets:         ## create the application Secret in the cluster (prompts; nothing written to disk)
	@printf 'OpenWeatherMap API key: '; read -rs OWM; echo; \
	printf 'Django secret key [generate]: '; read -rs DSK; echo; \
	printf 'PostgreSQL password [generate]: '; read -rs PGP; echo; \
	printf 'Demo partner token [empty]: '; read -rs DPT; echo; \
	DSK=$${DSK:-$$(openssl rand -base64 48 | tr -d '/+=' | cut -c1-50)}; \
	PGP=$${PGP:-$$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)}; \
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f - >/dev/null; \
	kubectl -n $(NAMESPACE) delete secret travel-agency-app --ignore-not-found >/dev/null; \
	kubectl -n $(NAMESPACE) create secret generic travel-agency-app \
	  --from-literal=OPENWEATHER_API_KEY="$$OWM" \
	  --from-literal=DJANGO_SECRET_KEY="$$DSK" \
	  --from-literal=POSTGRES_PASSWORD="$$PGP" \
	  --from-literal=DATABASE_URL="postgres://travel:$$PGP@travel-agency-postgres:5432/travel" \
	  --from-literal=DEMO_PARTNER_TOKEN="$$DPT"

secrets-check:   ## show that the application Secret exists and which keys it holds (never values)
	kubectl -n $(NAMESPACE) get secret travel-agency-app -o go-template='{{range $$k, $$v := .data}}{{$$k}}{{"\n"}}{{end}}'

deploy:          ## helm upgrade --install the chart with TAG (default: HEAD) and VALUES
	helm upgrade --install travel-agency chart -n $(NAMESPACE) --create-namespace -f $(VALUES) --set image.tag=$(TAG) --wait --timeout 10m
	helm -n $(NAMESPACE) history travel-agency | tail -3
