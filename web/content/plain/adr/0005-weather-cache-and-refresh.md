# 0005 Weather for known locations is refreshed by a scheduled job into PostgreSQL; Redis caches ad hoc coordinates; stale fallback

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: W1, W4; L3

## Context

OpenWeatherMap's free tier:

- allows 60 calls per minute;
- returns forecast in 3 hour slots;
- is outside our control.

The brackets endpoint needs the temperature of every location. A naive implementation calls
upstream N times per request.

## Options

1. Call upstream on every request. Simplest, but slow. It hits the limit and fails when
   upstream fails.
2. Cache per coordinate with a TTL (time to live, how long an entry stays valid), fetch on
   miss. Good for ad hoc coordinates. The brackets request still fans out on a cold cache.
3. Scheduled refresh of all known locations by a worker:
   - written to PostgreSQL as samples (ADR 0012) and read from there by the API;
   - ad hoc coordinates use option 2, with Redis as the short lived cache;
   - expired entries are served as stale while a refresh is attempted.

## Decision

Option 3.

**Known locations**

- Celery beat refreshes them every 15 minutes, inside a call budget.
- A location is also refreshed once, immediately, when it is created. So a new location has
  data within a minute.
- PostgreSQL is the single source for them. The worker writes samples; the API reads them and
  computes summaries. There is no second copy in Redis.

**Ad hoc coordinates (W1, W2)**

- Fetched on miss, with a 10 minute TTL in Redis.
- Timeouts and bounded retries.
- Not persisted.

Redis also serves as the Celery broker. A short lived cache of computed summaries is a later
optimisation, added only if measurements ask for it.

**Budget.** The per minute limit is split into two shares: one reserved for the scheduled
refresh, one for ad hoc requests. The sum is capped at 80 % of the limit.

- The refresh spreads its calls evenly over the interval.
- If the location count needs more calls than its share allows, the interval lengthens
  automatically. The operations status shows the effective interval.
- Ad hoc requests are rate limited per caller token. When the ad hoc share is exhausted, the
  API answers 429 with Retry-After.
- A failing call for one location does not abort the run.
- Minute and month counters are kept and exposed.

**When upstream fails**

- The last value is returned with `source: stale` and its age.
- The response is never a 5xx because of the upstream while a stored value exists.
- With no stored value (a coordinate asked for the first time during an outage), the API
  answers 503 with a problem detail and a Retry-After header. No made-up data, no empty 200.

**Daily aggregation.** The adapter aggregates the 3 hour slots per calendar day, in the
location's timezone:

- mean temperature;
- min;
- max;
- most frequent condition.

## Consequences

- The API path never blocks on upstream for known locations.
- The operations status reports hit ratio, last refresh and budget used.
- Coordinates are rounded to 3 decimals for cache keys.
- A circuit breaker opens after repeated upstream failures and closes on a successful probe.
  While it is open, ad hoc requests fail fast (503 or stale) instead of waiting for timeouts.
- Daily summaries are computed by the rules of ADR 0013 from the samples of ADR 0012.
