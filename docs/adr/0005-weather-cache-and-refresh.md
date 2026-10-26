# 0005 Weather for known locations is refreshed by a scheduled job into PostgreSQL; Redis caches ad hoc coordinates; stale fallback

Status: proposed
Date: 2026-10-26
Addresses: W1, W4; L3

## Context

OpenWeatherMap's free tier allows 60 calls per minute, returns forecast in 3 hour slots and is
outside our control. The brackets endpoint needs the temperature of every location; a naive
implementation calls upstream N times per request.

## Options

1. Call upstream on every request: simplest, slow, hits the limit, fails when upstream fails.
2. Cache per coordinate with a TTL, fetch on miss: good for ad hoc coordinates; the brackets
   request still fans out on a cold cache.
3. Scheduled refresh of all known locations by a worker, written to PostgreSQL as samples
   (ADR 0012) and read from there by the API; ad hoc coordinates use option 2 with Redis as
   the short lived cache; expired entries are served as stale while a refresh is attempted.

## Decision

Option 3. Known locations are refreshed every 15 minutes by Celery beat, inside a call budget,
and immediately once when a location is created, so a new location has data within a minute.
For known locations PostgreSQL is the single source: the worker writes samples, the API reads
them and computes summaries; no second copy in Redis. Ad hoc coordinates (W1, W2) are fetched
on miss with a 10 minute TTL in Redis, timeouts and bounded retries; they are not persisted.
Redis also serves as the Celery broker. A short lived cache of computed summaries is a later
optimisation, added only if measurements ask for it. When upstream fails, the last value is returned with `source: stale` and its age; the
response is never a 5xx because of the upstream while a stored value exists. With no stored
value (a coordinate asked for the first time during an outage) the API answers 503 with a
problem detail and a Retry-After header: no made-up data, no empty 200. Daily aggregation of the 3 hour slots happens
in the adapter: mean temperature, min, max, most frequent condition per calendar day in the
location's timezone.

## Consequences

The API path never blocks on upstream for known locations. The operations status reports hit
ratio, last refresh and budget used. Coordinates are rounded to 3 decimals for cache keys.
A circuit breaker opens after repeated upstream failures and closes on a successful probe.
Daily summaries are computed by the rules of ADR 0013 from the samples of ADR 0012.
