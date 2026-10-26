# 04 API

Status: draft, 2026-10-26. Base path `/api/v1`. OpenAPI schema at `/api/schema`, Swagger UI at
`/api/docs`. All errors are RFC 7807 problem details.

## Weather

| Method | Path | What |
|---|---|---|
| GET | `/weather/current?lat=&lon=` | Current temperature, condition, humidity, wind, `observed_at`, `source: live, cached or stale` |
| GET | `/weather/forecast?lat=&lon=` | `today` plus `days` (five, from tomorrow); per day local `date`, `temp_avg`, `temp_min`, `temp_max`, `condition`, `observed_samples`, `forecast_samples`, `partial`; response carries `timezone`, `as_of`, `source` (ADR 0013). For a known location `today` is complete once samples exist (ADR 0012) |

Coordinates are validated; ad hoc results are cached by rounded coordinates (3 decimals, about
100 m). Ad hoc requests are rate limited per token; over the limit or when the ad hoc upstream
share is exhausted the response is 429 with `Retry-After` (W4).

## Locations

| Method | Path | What |
|---|---|---|
| GET, POST | `/locations` | List, create (`ops`); `timezone` optional, derived from coordinates when omitted; creation triggers an immediate refresh |
| GET, PATCH, DELETE | `/locations/{id}` | Detail, update (including `active`), soft delete (`ops`); DELETE answers 409 with the active destinations when any exist |
| GET | `/locations/brackets?mode=fixed|quantile&buckets=` | Active locations grouped by current temperature: `brackets[]` (label, `from`, `to`, locations with temperature, `observed_at`, `stale`), open ended first and last bracket, empty brackets kept in fixed mode, a `no_data[]` group with reasons; each bracket with its `count`; `edges`, `mode`, `requested_buckets` and `effective_buckets` in quantile mode, `refreshed_at` (L3, L4) |
| POST | `/locations/refresh` | Trigger a refresh now (`ops`); returns the task id |
| GET, PUT | `/locations/bracket-edges` | Read or set the fixed edges (`ops`), strictly ascending list of 1 to 10 numbers; audited (L4) |

## Catalogue

| Method | Path | What |
|---|---|---|
| GET, POST | `/destinations` | List with filters `type`, `danger_max`, `location` |
| GET, PATCH, DELETE | `/destinations/{id}` | |
| GET, POST | `/packages` | List with `danger_max`, `type`, `price_max`, `q` |
| GET, PATCH, DELETE | `/packages/{id}` | Includes ordered destinations, computed `danger` (null for a draft) and `danger_label` |
| GET, POST | `/packages/{id}/departures` | Dates with `ends_on`, capacity and remaining seats |

## Bookable search (the required endpoint)

`GET /packages/bookable?from=YYYY-MM-DD&to=YYYY-MM-DD&danger=2`

Validation: both dates required, `from <= to`, span at most 366 days, `danger` 0 to 3; else
400 problem detail. "Today" is the agency's time zone (`settings.agency_timezone`). Only active
packages with a danger score and `planned` departures qualify. Order: earliest matching
departure, package name, id; page size 20 by default.

Returns packages that have at least one departure with `starts_on` in `[from, to]` (inclusive;
the range applies to the departure date, ADR 0011), in the future, with remaining seats > 0, and whose derived danger is <= `danger` (`danger_mode=exact`
switches to equality). Each item carries the package data (including `duration_days`), its danger, and the matching
departures with `starts_on`, `ends_on` and remaining seats. Paginated. Optional extras (N4): `traveller={id}` applies the
traveller's risk appetite as the "at most" danger (400 when the traveller has none); `type`, `price_max`; `min_forecast_avg=<°C>` keeps
packages whose destinations' locations all have a five day average at or above the value
(conditions now, not on the departure date; the response says so); `type`, `max_price`.

## Bookings

| Method | Path | What |
|---|---|---|
| POST | `/bookings` | `departure_id, traveller_id, seats`, header `Idempotency-Key`; 201 or 409 when sold out; partner_id from the token |
| GET | `/bookings/{id}` | |
| POST | `/bookings/{id}/cancel` | Idempotent; frees the seats, keeps the record |
| POST | `/packages/{id}/departures/{dep}/cancel` | `ops`; refused as delete when bookings exist, cancels them with reason `departure_cancelled` (P3) |

## Operations

| Path | What |
|---|---|
| `/healthz` | Process up |
| `/readyz` | Database and Redis reachable |
| `/api/v1/ops/status` | Cache hit ratio, last refresh time and effective interval, upstream calls this minute and this month against their shares, circuit breaker state, versions (read for the operations page) |
| `/metrics` | Prometheus |

## Auth

Token in `Authorization: Token ...`, one role per user (00-domain.md section 5): `ops` writes
the catalogue and departures and uses the admin; `sales` searches, books and cancels; `partner`
does the same for its own travellers and sees only its own bookings; `finance` reads
everything. Every role reads weather, brackets and the catalogue.
