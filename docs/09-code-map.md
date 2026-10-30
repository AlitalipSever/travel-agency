# 09 Code map and data flows

Status: draft, 2026-10-30. Short notes for a developer opening the code for the first time:
where things live and how a request or a job moves through the files.

## 1. One request through the layers

```
browser
  -> web/src/app/api/proxy/[...path]/route.ts   server side; the browser never sees a token
  -> web/src/lib/api.ts  apiFetch()             adds "Authorization: Token ...", /api/v1 prefix
  -> api/config/urls.py                         /api/v1/ -> each app's api/urls.py
  -> <app>/api/views.py                         HTTP only: auth, role, status code
  -> <app>/api/serializers.py                   JSON shape and field checks
  -> <app>/services.py                          business rules
  -> <app>/models.py                            tables and database constraints
  -> PostgreSQL
```

Views stay thin. Rules live in `services.py`, so a Celery task, the admin or a management
command can call the same function as the API.

## 2. Apps and their dependencies

```
core  <-  locations  <-  weather
                     <-  catalogue  <-  booking
```

| App | Holds | Start reading at |
|---|---|---|
| core | users and roles, RFC 7807 errors, pagination, health, Redis connection, settings | `errors.py`, `permissions.py` |
| locations | cities, temperature brackets | `brackets.py`, `services.py` |
| weather | upstream client, budget, breaker, samples, background jobs | `tasks.py`, `adhoc.py` |
| catalogue | destinations, packages, departures, bookable search | `models.py`, `bookable.py` |
| booking | travellers, partners, bookings | `services.py` |

Inside `weather`: `upstream/` is the only code that calls OpenWeatherMap, `domain/` is pure
logic with no Django and no network, the root holds tasks, samples and the ad hoc path.

## 3. Flow: scheduled weather refresh (data in)

```
beat (every REFRESH_INTERVAL_S = 900 s)
  -> Redis queue -> worker -> weather/tasks.py refresh_all()
       Redis lock owm:refresh:lock (a run in progress -> skip)
       active locations; spacing = max(interval / n, 60 / (refresh share / 2))
       per location: refresh_location_sync()
  -> weather/upstream/gateway.py fetch_current() + fetch_forecast()   share "refresh"
       breaker.allow()        open -> skip location, count failure
       budget.acquire()       over 40 this minute -> wait for the next minute
       client.py              HTTP; 2 retries with backoff and jitter
       breaker.record_*()     5 failures in a row -> open for 60 s
  -> weather/samples.py store_observation() / store_forecast()   upsert per slot
  -> PostgreSQL WeatherSample; RefreshRun records calls and failures
```

The number of upstream calls depends on the number of cities, not on traffic.

## 4. Flow: a new location

```
POST /api/v1/locations/ (ops)
  -> locations/services.py create_location()
       round to 5 decimals, derive the IANA time zone, save
       transaction.on_commit(-> weather/tasks.py refresh_one_now)
  -> worker fetches it at once; data is there within a minute
```

`on_commit` keeps the job from running for a row that was rolled back.

## 5. Flow: current weather (data out)

```
GET /api/v1/weather/current?lat=..&lon=..
  -> weather/api/views.py CurrentWeatherView (per token throttle)
  -> weather/adhoc.py get_current()
       known location within 100 m -> latest sample from PostgreSQL   source "sample"
       else Redis owm:current:<lat,lon>  fresh <= 600 s               source "cached"
       else gateway, share "adhoc" (8 per minute)                     source "live"
         budget spent  -> old value "stale", or 429 + Retry-After
         breaker/error -> old value "stale", or 503 + Retry-After
```

A known location never calls the upstream on the request path.

## 6. Flow: temperature brackets

```
GET /api/v1/locations/brackets
  -> locations/api/views.py brackets()
       latest sample per active location
       edges: fixed (settings) or quantile (from the data)
  -> locations/brackets.py group()   half open [lower, upper): each temperature in one bracket
```

## 7. Flow: bookable search

```
GET /api/v1/packages/bookable?from=..&to=..&danger=..
  -> catalogue/api/views.py PackageViewSet.bookable()
  -> catalogue/bookable.py
       parse()                 dates, span <= 366 days, danger 0-3, today in the agency zone
       query 1: packages()     with_danger() = MAX over destinations, EXISTS matching
                               departure, ordered by first departure, name, id; paginated
       query 2: departures_for(page ids)   matching departures with remaining seats
```

Two queries per page. Danger and seats are derived, never stored.

## 8. Flow: booking and cancel

```
POST /api/v1/bookings/  (Idempotency-Key header)
  -> booking/services.py create_booking()   one transaction
       same key + same body -> the earlier booking; other body -> 422
       SELECT ... FOR UPDATE on the departure   (a second request waits here)
       traveller from the caller's scope; departure, package and draft checks -> 409
       remaining = capacity - confirmed seats; too few -> 409
       create with price and danger snapshots; partner from the token, never the body

POST /api/v1/bookings/<id>/cancel/
  -> booking/services.py cancel_booking()   same lock order, idempotent
       status cancelled; the row stays; seats free up because they are derived
```

## 9. Try it: add a location as ops

Writes to locations need the ops role. Get the ops user's token inside the cluster, then call
the API. The token stays in a shell variable and is never printed.

```bash
export OPS_TOKEN=$(kubectl -n travel-agency exec deploy/travel-agency-api -- \
  python manage.py drf_create_token demo-ops | awk '{print $3}')

curl -s -X POST https://<host>/api/v1/locations/ \
  -H "Authorization: Token $OPS_TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Frankfurt", "country_code": "DE", "latitude": 50.1109, "longitude": 8.6821}'

# a minute later: source "sample" means the worker stored it
curl -s "https://<host>/api/v1/weather/current?lat=50.1109&lon=8.6821" \
  -H "Authorization: Token $OPS_TOKEN"

# remove it again (soft delete)
curl -s -X DELETE https://<host>/api/v1/locations/<id>/ -H "Authorization: Token $OPS_TOKEN"
```

## 10. Look at the database

PostgreSQL is not exposed outside the cluster. Open a tunnel and point any client at
`localhost:15432`, database and user `travel`; the password is `POSTGRES_PASSWORD` in the
`travel-agency-app` Secret. Or run psql inside the pod.

```bash
kubectl -n travel-agency port-forward pod/travel-agency-postgres-0 15432:5432
kubectl -n travel-agency exec -it travel-agency-postgres-0 -- psql -U travel -d travel
```

Tables are named `<app>_<model>`, for example `catalogue_departure`, `booking_booking`.
