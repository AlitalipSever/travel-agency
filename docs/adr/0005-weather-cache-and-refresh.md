# 0005 Weather is cached in Redis and refreshed by a scheduled job, with stale fallback

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
3. Scheduled refresh of all known locations by a worker, cache written by the worker, read by
   the API; ad hoc coordinates use option 2; expired entries are served as stale while a
   refresh is attempted.

## Decision

Option 3. Known locations are refreshed every 15 minutes by Celery beat, inside a call budget.
Ad hoc coordinates (W1, W2) are fetched on miss with a 10 minute TTL, timeouts and bounded
retries. When upstream fails, the last value is returned with `source: stale` and its age; the
response is never a 5xx because of the upstream while a stored value exists. With no stored
value (a coordinate asked for the first time during an outage) the API answers 503 with a
problem detail and a Retry-After header: no made-up data, no empty 200. Daily aggregation of the 3 hour slots happens
in the adapter: mean temperature, min, max, most frequent condition per calendar day in the
location's timezone.

## Consequences

The API path never blocks on upstream for known locations. The operations status reports hit
ratio, last refresh and budget used. Coordinates are rounded to 3 decimals for cache keys.
A circuit breaker opens after repeated upstream failures and closes on a successful probe.
The cache is not the only store: what the worker fetches for known locations is also persisted
(ADR 0012), and daily summaries are computed by the rules of ADR 0013.
