# travel-agency

An open source SaaS platform for small travel agencies. It runs the parts an agency sells
from: destinations with live weather and five day forecasts, tour packages with clear
adventure levels, dated departures with seats, and bookings by staff and partners through
one API. Built with Django, Celery, PostgreSQL and Redis, served by a Next.js site, and
deployed on Hetzner with Terraform, Kubernetes (k3s) and Helm.

**Live demo:** https://travel-agency.asever.dev. Andes & Coast is a made-up agency running on
this platform; bookings there are not real. The top menu also links the architecture, the
decisions, the API (`/api/docs`, Swagger UI) and a live operations page.

## What it does

- **Weather for every destination.** A background worker keeps current weather and a five day
  forecast for each location, grouped by temperature bracket; any other point on the map is
  answered on demand, within a call budget and behind a circuit breaker.
- **Tours that say how hard they are.** Packages list their destinations in order; a package's
  adventure level is derived from its most demanding destination, never typed in.
- **Departures with real seats.** Capacity belongs to a departure date; remaining seats come
  from confirmed bookings.
- **Search what can still be booked.** Free departures in a date range up to a chosen adventure
  level, in one measured query.
- **Safe bookings.** A row lock per departure, idempotency keys for retries, a 409 when the last
  seat is gone, and partners only ever see their own travellers and bookings.
- **Roles.** Operations, sales, partner and finance, each with its own token and permissions.

## Tech stack

| Layer | Tools |
|---|---|
| API | Python 3.13, Django 5.2, Django REST Framework, drf-spectacular (OpenAPI), RFC 7807 errors |
| Background jobs | Celery worker and beat, Redis 7 |
| Database | PostgreSQL 16 |
| Web | Next.js 16, TypeScript, Tailwind, shadcn/ui, Leaflet |
| Weather data | OpenWeatherMap |
| Infrastructure | Hetzner Cloud (ARM), Terraform, k3s, ingress-nginx, cert-manager with Let's Encrypt, Cloudflare DNS |
| Packaging | Docker multi-arch images on ghcr.io, one Helm chart for the whole system |
| Quality | pytest (181 tests), ruff, mypy, eslint, tsc; GitHub Actions on every pull request |

## Run it

Requirements: Docker (Docker Desktop or Colima) and `make`.

```
make up        # postgres, redis, migrate + seed, api, worker, beat   → http://localhost:8000
make demo      # demo partner, four users with tokens, packages, departures, bookings
make test      # 181 tests inside the container
make lint      # ruff + mypy (laptop, needs uv)
```

`make up` copies `.env.example` to `api/.env` when missing. After editing `api/.env` run
`make up` (or `docker compose up -d <service>`) again: `docker compose restart` keeps the old
environment and does not reread the file. Without an `OPENWEATHER_API_KEY`
the weather adapter runs in mock mode from recorded payloads; with a key the worker refreshes
the thirteen seeded capitals every fifteen minutes.

Then:

- Swagger UI: http://localhost:8000/api/docs (schema at `/api/schema`)
- Admin: http://localhost:8000/admin/ (`make superuser`)
- Health: `/healthz`, `/readyz`

Every API call needs `Authorization: Token <value>`; `make demo` prints one token per role
(`demo-ops`, `demo-sales`, `demo-partner`, `demo-finance`). Every role reads; only `ops` writes.
In Swagger UI click **Authorize** and enter the whole header value, `Token <value>`, with the
word `Token` and a space in front of the key.

## Try the API

```
T="Authorization: Token <demo-sales token>"
B=http://localhost:8000/api/v1

curl -H "$T" "$B/weather/current?lat=-12.046&lon=-77.043"          # current weather, Lima
curl -H "$T" "$B/weather/forecast?lat=-12.046&lon=-77.043"         # today + five days
curl -H "$T" "$B/locations/brackets"                               # capitals by temperature bracket
curl -H "$T" "$B/locations/brackets?mode=quantile&buckets=3"
curl -H "$T" "$B/packages"                                         # packages with derived danger
curl -H "$T" "$B/packages/bookable?from=2026-11-01&to=2026-12-31&danger=2"
```

Errors come back as RFC 7807 `application/problem+json` (400, 401, 403, 404, 409, 429, 503).

## How it is built

- Weather is fetched by a Celery worker on a schedule into PostgreSQL samples; the API never
  calls the upstream for a known location (ADR 0005). Unknown coordinates go through a Redis
  cache, a call budget split between refresh and ad hoc traffic, and a circuit breaker; stale
  data is served and labelled before a 503 (ADR 0012).
- Daily summaries follow the location's local calendar with IANA zones (ADR 0013); brackets are
  half-open edges from a settings table, with a quantile mode (ADR 0004).
- A package's danger is never stored: it is the maximum over its destinations, computed in the
  query (ADR 0003). Capacity belongs to a departure date; remaining seats are derived from
  confirmed bookings and the booking path takes a row lock (ADR 0002).
- The bookable search is two queries per page; its plan was measured on 20,000 departures and
  one partial index took it from 1.3 s to 21 ms (`docs/plans/bookable.md`).

## Deploy

One server, one chart. The full runbook is [docs/06-operations.md](docs/06-operations.md).

```
make infra-apply   # Terraform: Hetzner server, firewall, data volume, k3s via cloud-init
make bootstrap     # ingress-nginx, cert-manager, Let's Encrypt issuers
make secrets       # application secrets into the cluster (typed, never stored in git)
make images-push   # build and push the api and web images to ghcr.io
make deploy        # helm upgrade --install: migrate job, api, worker, beat, web, PostgreSQL, Redis
```

## Layout

```
Makefile              Single entry point (make help)
docker-compose.yml    Local stack: api, worker, beat, postgres, redis
.env.example          Variable names, never values
api/                  Django project: config/ (settings, urls, celery) and the apps
                      core/ (users, roles, settings table, errors), weather/, locations/,
                      catalogue/ (types, destinations, packages, departures, bookable search),
                      booking/ (travellers, bookings); each app has its tests/
web/                  Next.js site: the demo agency and the engineering pages
chart/                Helm chart for the whole system
infra/terraform/      Hetzner server, firewall, volume, k3s
infra/k8s/            Cluster add-ons: ingress-nginx, cert-manager, issuers
.github/workflows/    CI: lint, types, tests, multi-arch images
docs/                 Domain, requirements, architecture (arc42 + C4), data model, API, ADRs, plans
```

## Documentation

Start at [docs/README.md](docs/README.md). The architecture is
[docs/02-architecture.md](docs/02-architecture.md), every decision is an ADR in
[docs/adr](docs/adr/README.md), and [docs/08-walkthrough.md](docs/08-walkthrough.md) is a ten
minute path through the system.

## Status

Running in production on one Hetzner k3s node. Single tenant today: one agency per
installation. [docs/07-roadmap.md](docs/07-roadmap.md) lists what is done, what was left out on
purpose (multi tenancy, operator-managed PostgreSQL with backups, deploy from CI, high
availability) and what comes next.
