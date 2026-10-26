# 04 API

Status: draft, 2026-10-26. Base path `/api/v1`. OpenAPI schema at `/api/schema`, Swagger UI at
`/api/docs`. All errors are RFC 7807 problem details.

## Weather

| Method | Path | What |
|---|---|---|
| GET | `/weather/current?lat=&lon=` | Current temperature, condition, humidity, wind, `observed_at`, `source: live or cache or stale` |
| GET | `/weather/forecast?lat=&lon=` | `today` plus `days` (five, from tomorrow); per day local `date`, `temp_avg`, `temp_min`, `temp_max`, `condition`, `observed_samples`, `forecast_samples`, `partial`; response carries `timezone`, `as_of`, `source` (ADR 0013). For a known location `today` is complete once samples exist (ADR 0012) |

Coordinates are validated; results are cached by rounded coordinates (3 decimals, about 100 m).

## Locations

| Method | Path | What |
|---|---|---|
| GET, POST | `/locations` | List, create (staff) |
| GET, PATCH, DELETE | `/locations/{id}` | Detail, update, soft delete (staff) |
| GET | `/locations/brackets` | Locations grouped by current temperature bracket; bracket edges and `refreshed_at` in the response |
| POST | `/locations/refresh` | Trigger a refresh now (staff); returns the task id |

## Catalogue

| Method | Path | What |
|---|---|---|
| GET, POST | `/destinations` | List with filters `type`, `danger_max`, `location` |
| GET, PATCH, DELETE | `/destinations/{id}` | |
| GET, POST | `/packages` | List with `danger_max`, `type`, `price_max`, `q` |
| GET, PATCH, DELETE | `/packages/{id}` | Includes destinations and computed `danger` |
| GET, POST | `/packages/{id}/departures` | Dates with `ends_on`, capacity and remaining seats |

## Bookable search (the required endpoint)

`GET /packages/bookable?from=YYYY-MM-DD&to=YYYY-MM-DD&danger=2`

Returns packages that have at least one departure with `starts_on` in `[from, to]` (inclusive;
the range applies to the departure date, ADR 0011), in the future, with remaining seats > 0, and whose derived danger is <= `danger` (`danger_mode=exact`
switches to equality). Each item carries the package data (including `duration_days`), its danger, and the matching
departures with `starts_on`, `ends_on` and remaining seats. Paginated. Optional extras: `customer={id}` applies the
customer's risk appetite instead of `danger`; `type`, `price_max`; `weather=warm` keeps
packages whose destinations' forecast average is above a threshold.

## Bookings

| Method | Path | What |
|---|---|---|
| POST | `/bookings` | `departure_id, customer_id, seats`, header `Idempotency-Key`; 201 or 409 when sold out |
| GET | `/bookings/{id}` | |
| POST | `/bookings/{id}/cancel` | |

## Operations

| Path | What |
|---|---|
| `/healthz` | Process up |
| `/readyz` | Database and Redis reachable |
| `/api/v1/ops/status` | Cache hit ratio, last refresh time, upstream call budget, versions (read for the operations page) |
| `/metrics` | Prometheus |

## Auth

Token in `Authorization: Token ...`. Groups: `staff` (write everywhere, admin), `client`
(read, create bookings). Weather and brackets endpoints are readable with the client token.
