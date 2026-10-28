# 0012 Forecast slots and observations are persisted for known locations

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: W2, W4

## Context

The free tier of OpenWeatherMap returns the following:

- the forecast, as 40 three hour slots, starting from the next full slot after "now";
- the current observation for "now".

There is no daily summary, nothing beyond 120 hours and no history. This leaves gaps:

- A daily summary of today lacks the hours that have already passed.
- The summary of the fifth day is cut by the window's end.

The worker already fetches every known location every 15 minutes (ADR 0005). So the data that
would fill today's morning was in our hands yesterday.

## Options

1. Keep weather only in Redis with a TTL (time to live, after which the entry expires).
   - Simplest.
   - Today is always partial.
   - Nothing to compare against later.
2. Persist what the worker fetches, in PostgreSQL.
   - Every forecast slot is stored: location, slot time in UTC, fetched at, temperature,
     condition code, precipitation probability.
   - Every observation is stored too.
   - The newest fetch wins per slot.
   - An observation supersedes a forecast for the same hour.
3. Buy the One Call 3.0 subscription for daily and historical data. This is outside the brief's
   "free tier only".

## Decision

Option 2, for known locations.

- A single `WeatherSample` table with `kind = forecast | observation` keeps the schema small.
- A unique key on (location, slot_time, kind), with upsert on fetch.
- The daily summary (ADR 0013) reads samples for the local calendar day. So today is complete
  once the system has run for a day.
- Past days become comparable ("same day last week").

Ad hoc coordinates (requests with arbitrary latitude and longitude) are not persisted. They keep
the cache only path, and their today is marked partial.

For known locations, the table is both the record and what the API reads. Redis caches only ad
hoc coordinates (ADR 0005).

"Known" and "ad hoc" are not two code paths. They are one path with different amounts of stored
data. A location created an hour ago behaves like an ad hoc coordinate for today. From the next
local day it behaves like a known location.

## Consequences

- Data volume is small (13 locations x 8 slots x 2 kinds per day).
- A retention job prunes samples older than 90 days.
- The first day after deployment still shows a partial today. The response says so
  (`partial`, `observed_samples`, `forecast_samples`).
- The roadmap item "weather history" is absorbed by this decision.
