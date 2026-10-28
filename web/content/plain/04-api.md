# 04 API

Status: reviewed against 00-domain, 01-requirements, 02-architecture and 03-data-model, 2026-10-27.

Every endpoint names the requirement it serves. It also names the roles that may call it
(00-domain §5).

## 1. Conventions

| Topic | Rule |
|---|---|
| Base path | `/api/v1` |
| Schema | OpenAPI 3 at `/api/schema`, Swagger UI at `/api/docs` |
| Format | JSON |
| Auth | `Authorization: Token <token>` |
| Partner scope | A `partner` token only sees and changes bookings and travellers with its own `partner_id` |
| Demo | The case study site acts as the `demo` partner (A17, ADR 0015) |
| Errors | RFC 7807 problem details, `Content-Type: application/problem+json` |
| Pagination | `?page=&page_size=` (default 20, max 100) |
| Filtering | Query parameters listed per endpoint |
| Idempotency | `POST /bookings` requires `Idempotency-Key` (1 to 128 chars) |
| Rate limits | Per token on ad hoc weather requests (default 30 per minute) |
| Reads of data quality | Weather responses and bracket rows carry freshness fields (ISO 25012 visibility) |
| Soft delete | `DELETE` on locations, destinations and packages is a soft delete |

- **Base path:** a breaking change opens `/api/v2`. The old path stays for one release.
- **Schema:** the schema is generated from the code (drf-spectacular). It is the contract
  partners integrate against.
- **Format:**
  - dates are `YYYY-MM-DD`;
  - timestamps are ISO 8601 with offset (UTC in responses);
  - money is a decimal string plus `currency`;
  - coordinates are decimal degrees.
- **Auth:**
  - One token per user, one role per user (`ops`, `sales`, `partner`, `finance`).
  - Tokens are issued by operations in the admin. There is no self-service login.
  - 401 without a valid token, 403 outside the role's permissions.
- **Partner scope:** a `partner` token never sees another partner's rows. It gets 404, not
  403, so existence is not leaked.
- **Demo:** the site's server holds the token. It forwards an allow-listed subset of the API
  through a proxy route. The browser never sees the token, and the API's CORS stays closed.
- **Errors:** a problem detail carries:
  - `type` (a URI under `/problems/`), `title`, `status`, `detail`, `instance`;
  - `errors[]` (field, message) on validation failures.

  Internals are never echoed.
- **Pagination:** responses carry `count`, `next`, `previous`, `results[]`. Every list has a
  stable order, with `id` as the last tie breaker.
- **Filtering:** unknown parameters are rejected with 400. So typos never silently return
  everything.
- **Idempotency:** the key makes a retried request safe to send twice.
  - A repeated key from the same user returns the original response. The status is 200 and
    the header is `Idempotent-Replayed: true`.
  - The same key with a different body is 422.
- **Rate limits:** over the limit the API returns 429 with `Retry-After` and
  `X-RateLimit-Limit`, `X-RateLimit-Remaining`. The same 429 comes back when the ad hoc
  upstream share is exhausted (W4.3).
- **Reads of data quality:**
  - Weather responses carry `source` (`live`, `cached`, `stale`), `as_of` and, per day,
    `partial` with sample counts.
  - Bracket rows carry `observed_at` and `stale`.
- **Soft delete:** deleted rows disappear from lists and return 404 on detail.

### Problem types

| `type` | Status | When |
|---|---|---|
| `/problems/validation` | 400 | Invalid or unknown parameters, bad body; `errors[]` names the fields |
| `/problems/unauthenticated` | 401 | Missing or invalid token |
| `/problems/forbidden` | 403 | Role may not do this |
| `/problems/not-found` | 404 | Unknown id, soft-deleted row, or another partner's row |
| `/problems/conflict` | 409 | A state conflict (see below) |
| `/problems/idempotency-mismatch` | 422 | Same key, different body |
| `/problems/rate-limited` | 429 | Per-token limit or ad hoc upstream share exhausted; `Retry-After` |
| `/problems/upstream-unavailable` | 503 | Weather upstream unreachable and nothing stored for the coordinate; `Retry-After` |

- **409 conflict** covers four cases:
  - sold out (`remaining` in `detail` data);
  - capacity below confirmed seats;
  - delete refused while referenced (the referencing ids are listed);
  - duplicate name.

## 2. Weather (W1 to W4)

| Method | Path | Roles | What |
|---|---|---|---|
| GET | `/weather/current?lat=&lon=` | all | Current weather for a coordinate. W1 |
| GET | `/weather/forecast?lat=&lon=` | all | `today` plus `days` (five, from tomorrow) for a coordinate. W2, W3 |
| GET | `/locations/{id}/weather` | all | Convenience: the same two payloads for a known location by id |

- **`/weather/current?lat=&lon=`:** a known location is a match within 100 m of a list entry.
  - For a known location, the answer is the latest observation from the samples.
  - Otherwise it takes the ad hoc path (cache, upstream, stale, 503).
- **`/weather/forecast?lat=&lon=`:** known locations get a complete `today` once samples exist.
- **`/locations/{id}/weather`:** always from samples. It never calls the upstream.

Current weather response:

```json
{
  "lat": -12.046, "lon": -77.043, "timezone": "America/Lima",
  "temp": 19.4, "condition": "cloudy", "condition_code": 803,
  "humidity": 78, "wind_speed": 4.1,
  "observed_at": "2026-10-27T15:00:00Z", "source": "cached", "age_s": 240
}
```

Forecast response:

```json
{
  "lat": -12.046, "lon": -77.043, "timezone": "America/Lima",
  "as_of": "2026-10-27T15:12:03Z", "source": "cached",
  "today": {"date": "2026-10-27", "temp_avg": 18.9, "temp_min": 15.2, "temp_max": 22.1,
            "condition": "cloudy", "observed_samples": 5, "forecast_samples": 3, "partial": false},
  "days": [
    {"date": "2026-10-28", "temp_avg": 19.3, "temp_min": 15.0, "temp_max": 23.0,
     "condition": "clear", "observed_samples": 0, "forecast_samples": 8, "partial": false},
    {"date": "2026-11-01", "temp_avg": 20.1, "temp_min": 16.4, "temp_max": 22.8,
     "condition": "rain", "observed_samples": 0, "forecast_samples": 5, "partial": true}
  ]
}
```

Units are metric (A14).

Condition labels: `thunderstorm`, `rain`, `snow`, `fog`, `cloudy`, `clear`, `unknown` (W3.4).

## 3. Locations and brackets (L1 to L4)

| Method | Path | Roles | What |
|---|---|---|---|
| GET | `/locations?active=&country=&q=` | all | List, ordered by name; `active` defaults to true |
| POST | `/locations` | ops | Create; enqueues an immediate refresh (L1.5) |
| GET | `/locations/{id}` | all | Detail with `active`, `timezone`, counts of destinations |
| PATCH | `/locations/{id}` | ops | Update any field including `active` (deactivate, L1.3) |
| DELETE | `/locations/{id}` | ops | Soft delete; 409 listing active destinations when any reference it (L1.4) |
| GET | `/locations/brackets?mode=fixed&buckets=4` | all | Active locations grouped by current temperature (below) |
| GET, PUT | `/locations/bracket-edges` | all read, ops write | The fixed edge list (L4.1, L4.2) |
| POST | `/locations/refresh` | ops | Run a refresh now; returns `{"run_id": ...}` |

- **POST `/locations`:** the body has `name`, `country_code`, `latitude`, `longitude` and an
  optional `timezone`. When `timezone` is omitted it is derived and returned in the response.
- **`/locations/bracket-edges`:** the list is strictly ascending, with 1 to 10 numbers. A change
  applies on the next read and is attributed.
- **`/locations/refresh`:** the result appears in `/ops/status`.

Brackets response. `mode=fixed` is the default. `mode=quantile&buckets=N` derives the edges from
the data, and reports `requested_buckets` and `effective_buckets`.

```json
{
  "mode": "fixed", "edges": [10, 20, 25, 30], "refreshed_at": "2026-10-27T15:00:00Z",
  "brackets": [
    {"label": "below 10", "from": null, "to": 10, "count": 1,
     "locations": [{"id": "...", "name": "La Paz", "temp": 7.8, "observed_at": "2026-10-27T15:00:00Z", "stale": false}]},
    {"label": "10 to 20", "from": 10, "to": 20, "count": 6, "locations": ["..."]},
    {"label": "20 to 25", "from": 20, "to": 25, "count": 0, "locations": []},
    {"label": "25 to 30", "from": 25, "to": 30, "count": 5, "locations": ["..."]},
    {"label": "30 and above", "from": 30, "to": null, "count": 1, "locations": ["..."]}
  ],
  "no_data": [{"id": "...", "name": "Cayenne", "reason": "not refreshed yet"}]
}
```

Brackets are half-open: `from` is included, `to` is excluded. Inside a bracket, locations are
ordered by temperature ascending (L3).

## 4. Catalogue (P1, P2, P4)

| Method | Path | Roles | What |
|---|---|---|---|
| GET, POST | `/destination-types` | all read, ops write | The reference list; `key`, `label` (P2.3) |
| PATCH, DELETE | `/destination-types/{id}` | ops | Delete refused (409) while destinations use it |
| GET | `/destinations?type=&danger_max=&location=&active=&q=` | all | List |
| POST | `/destinations` | ops | `location_id`, `type_id`, `name`, `danger` (0 to 3), `description` |
| GET, PATCH, DELETE | `/destinations/{id}` | all read, ops write | Danger changes are attributed; DELETE 409 listing the packages that use it (P2.5) |
| GET | `/packages?active=&danger_max=&type=&max_price=&q=` | all | List with `danger` and `danger_label` per package (P4.3) |
| POST | `/packages` | ops | Create a package (fields below) |
| GET | `/packages/{id}` | all | Detail (fields below) |
| PATCH | `/packages/{id}` | ops | Any field (P1.5, P1.6) |
| DELETE | `/packages/{id}` | ops | Soft delete; 409 while any departure has bookings |

- **POST `/packages`:** `name`, `price`, `currency`, `description`, `duration_days`,
  `destination_ids[]`. The ids are ordered destination ids. An empty list = draft.
- **GET `/packages/{id}`:** ordered `destinations[]`, `danger` (null for a draft),
  `danger_label`, `departures_summary` (next departure, seats).
- **PATCH `/packages/{id}`:** `destination_ids[]` replaces the ordered list. `active`
  deactivates.

Package representation:

```json
{
  "id": "...", "name": "Andes Adventure", "price": "1200.00", "currency": "EUR",
  "description": "...", "duration_days": 7, "active": true,
  "danger": 2, "danger_label": "medium",
  "destinations": [
    {"position": 1, "id": "...", "name": "Cusco old town", "type": "cultural", "danger": 0, "location": {"id": "...", "name": "Lima"}},
    {"position": 2, "id": "...", "name": "Inca trail", "type": "adventure", "danger": 2, "location": {"id": "...", "name": "Lima"}}
  ]
}
```

## 5. Departures (P3)

| Method | Path | Roles | What |
|---|---|---|---|
| GET | `/packages/{id}/departures?from=&to=&status=` | all | Departures of a package (fields below) |
| POST | `/packages/{id}/departures` | ops | `starts_on`, `capacity`; 409 on a duplicate date |
| GET | `/departures/{id}` | all | Detail as above |
| PATCH | `/departures/{id}` | ops | `capacity` (409 below confirmed seats, P3.3), `starts_on` while no bookings |
| DELETE | `/departures/{id}` | ops | Only without bookings; otherwise 409 pointing at cancel |
| POST | `/departures/{id}/cancel` | ops | Marks the departure and its bookings cancelled; idempotent (P3.4) |

- **GET `/packages/{id}/departures`:** each departure has `starts_on`, `ends_on`, `capacity`,
  `confirmed_seats`, `remaining_seats`, `status`.
- **POST `/departures/{id}/cancel`:** the bookings are cancelled with
  `cancelled_by = departure_cancelled`. Idempotent means calling it again changes nothing.

## 6. Bookable search (P5, the brief's required endpoint)

`GET /packages/bookable?from=YYYY-MM-DD&to=YYYY-MM-DD&danger=2`

| Parameter | Required | Rule |
|---|---|---|
| `from`, `to` | yes | ISO dates, `from <= to`, span at most 366 days (P5.1) |
| `danger` | yes unless `traveller` is given | 0 to 3; "at most" by default (A1) |
| `danger_mode` | no | `at_most` (default) or `exact` (P5.3) |
| `traveller` | no | Traveller id; uses the traveller's `risk_appetite` as the danger ceiling (N4.2) |
| `type` | no | Destination type key (N4.4) |
| `max_price` | no | Price per traveller at most this value (N4.4) |
| `min_forecast_avg` | no | °C; a minimum five day average (N4.3) |
| `page`, `page_size` | no | Pagination |

- **`traveller`:** 400 if the traveller has none. A partner may only name its own travellers.
- **`type`:** keeps packages containing at least one destination of that type.
- **`max_price`:** the value is in the package's currency.
- **`min_forecast_avg`:**
  - It keeps packages whose destinations' locations all have a five day average at or
    above it.
  - The response sets `weather_filter_note`. The note says this describes conditions now,
    not on the departure date.

Rules:

- A package is listed only when it is active and has a danger score.
- Its departure must be `planned` and start inside the inclusive range.
- The departure must start on or after today in the agency's time zone (A16).
- The departure must have remaining seats (P5.2).
- Order: earliest matching departure, package name, id (P5.5).
- Extras only narrow (P5.6).

Response:

```json
{
  "count": 2, "next": null, "previous": null,
  "query": {"from": "2026-03-01", "to": "2026-03-15", "danger": 2, "danger_mode": "at_most", "today": "2026-10-27", "timezone": "America/Lima"},
  "results": [
    {"id": "...", "name": "Andes Adventure", "price": "1200.00", "currency": "EUR", "duration_days": 7,
     "danger": 2, "danger_label": "medium",
     "departures": [
       {"id": "...", "starts_on": "2026-03-10", "ends_on": "2026-03-16", "capacity": 20, "confirmed_seats": 5, "remaining_seats": 15}
     ]}
  ]
}
```

Only the departures that match the query are listed. Each comes with its end date and seats
(P5.4).

## 7. Travellers, partners and bookings (P6, N6)

| Method | Path | Roles | What |
|---|---|---|---|
| GET, POST | `/travellers?q=` | ops, sales, partner (own only) | `name`, `email`, optional `risk_appetite` (0 to 3) |
| GET, PATCH | `/travellers/{id}` | ops, sales, partner (own only) | |
| GET, POST | `/partners` | ops; finance read | `name`; `is_demo` on at most one row |
| GET | `/bookings?departure=&traveller=&status=&from=&to=` | ops, sales, finance all; partner own only | List ordered by `created_at` descending |
| POST | `/bookings` | ops, sales, partner | Create a booking (P6.1, P6.2) |
| GET | `/bookings/{id}` | ops, sales, finance; partner own only | |
| POST | `/bookings/{id}/cancel` | ops, sales; partner own only | Idempotent; frees the seats, keeps the record (P6.5) |

- **`/travellers?q=`:** a partner's travellers carry its `partner_id`.
- **POST `/bookings`:**
  - Body: `departure_id`, `traveller_id`, `seats`.
  - Header `Idempotency-Key` is required.
  - 201 with the booking.
  - 409 `conflict` with `remaining` when seats exceed availability.
  - `partner_id` is taken from the token, never from the body.
- **POST `/bookings/{id}/cancel`:** it sets `cancelled_by = traveller_request` (or `agency`
  when done by ops) and `cancelled_at`.

Booking representation:

```json
{
  "id": "...", "departure": {"id": "...", "starts_on": "2026-03-10", "ends_on": "2026-03-16", "package": {"id": "...", "name": "Andes Adventure"}},
  "traveller": {"id": "...", "name": "..."}, "partner_id": null,
  "seats": 2, "price_at_booking": "1200.00", "currency": "EUR", "danger_at_booking": 2,
  "status": "confirmed", "cancelled_by": null, "cancelled_at": null,
  "created_at": "2026-10-27T15:20:11Z", "created_by": "sales-anna"
}
```

## 8. Operations and health (N5, N6)

| Path | Roles | What |
|---|---|---|
| `/healthz` | none | Process up; used by the liveness probe |
| `/readyz` | none | Database and Redis reachable; used by the readiness probe |
| `/metrics` | cluster only | Prometheus metrics (list below) |
| `/api/v1/ops/status` | all (the site reads it) | The state of refreshes and the upstream (list below) |

- **`/metrics`:** request rate, errors and duration per endpoint, upstream calls, budget
  shares, breaker state.
- **`/api/v1/ops/status`:**
  - last refresh (`run_id`, `started_at`, `finished_at`, `locations`, `calls_used`,
    `failures`, `effective_interval_s`);
  - upstream calls this minute and this month against their shares;
  - circuit breaker state (the switch that stops calls to a failing upstream);
  - ad hoc cache hit ratio;
  - sample count;
  - versions (api, chart, commit).

## 9. What is deliberately not in the API

The API leaves out:

- login or password endpoints (tokens are issued by operations);
- payments;
- traveller self-service;
- bulk import;
- webhooks or an event feed (ADR 0008).

Each is in 07-roadmap with what it would take.
