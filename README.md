# travel-agency

Backend for a travel agency: live weather and five day forecasts for the agency's locations,
locations grouped by temperature bracket, tour packages with ordered destinations and a derived
danger score, dated departures with capacity, and the bookable-packages search by date range
and danger score. Django 5.2 + Django REST Framework, Celery, PostgreSQL 16, Redis 7, packaged
with Docker and run locally with `docker compose`.

## Run it

Requirements: Docker (Docker Desktop or Colima) and `make`.

```
make up        # postgres, redis, migrate + seed, api, worker, beat   → http://localhost:8000
make demo      # demo partner, four users with tokens, packages, departures, bookings
make test      # 173 tests inside the container
make lint      # ruff + mypy (laptop, needs uv)
```

`make up` copies `.env.example` to `api/.env` when missing. Without an `OPENWEATHER_API_KEY`
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

## Try the brief's three parts

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

## Layout

```
Makefile              Single entry point
docker-compose.yml    Local stack: api, worker, beat, postgres, redis
.env.example          Variable names, never values
docs/                 Domain, requirements, architecture (arc42 + C4), data model, API, ADRs, plans
api/                  Django project: config/ (settings, urls, celery) and the apps
                      core/ (users, roles, settings table, errors), weather/, locations/,
                      catalogue/ (types, destinations, packages, departures, bookable search),
                      booking/ (tables; rules and endpoints are next); each app has its tests/
```

The documentation starts at [docs/README.md](docs/README.md): the ten minute walkthrough is
[docs/08-walkthrough.md](docs/08-walkthrough.md), the decisions are in [docs/adr](docs/adr/README.md).

## Status

The brief's required scope runs locally end to end (work packages B1 to B8 and L1,
[docs/07-roadmap.md](docs/07-roadmap.md) §1). Next, in order: bookings with concurrency and
idempotency (B9), operations status and demo reset (B12), the Helm chart on kind and on a
Hetzner k3s node (P5, L2, Track B), the case study site (W1 to W6). What was deliberately left
out and why is in 07-roadmap §2.
