# 0012 Forecast slots and observations are persisted for known locations

Status: proposed
Date: 2026-10-26

## Context

The free tier of OpenWeatherMap returns the forecast as 40 three hour slots starting from the
next full slot after "now", and the current observation for "now". There is no daily summary,
nothing beyond 120 hours and no history. A daily summary of today therefore lacks the hours
that have already passed, and the summary of the fifth day is cut by the window's end. The
worker already fetches every known location every 15 minutes (ADR 0005), so the data that
would fill today's morning was in our hands yesterday.

## Options

1. Keep weather only in Redis with a TTL: simplest; today is always partial; nothing to compare
   against later.
2. Persist what the worker fetches: every forecast slot (location, slot time in UTC, fetched
   at, temperature, condition code, precipitation probability) and every observation, in
   PostgreSQL. The newest fetch wins per slot; an observation supersedes a forecast for the
   same hour.
3. Buy the One Call 3.0 subscription for daily and historical data: outside the brief's "free
   tier only".

## Decision

Option 2 for known locations. A single `WeatherSample` table with `kind = forecast |
observation` keeps the schema small; a unique key on (location, slot_time, kind) with upsert on
fetch. The daily summary (ADR 0013) reads samples for the local calendar day, so today is
complete once the system has run for a day, and past days become comparable ("same day last
week"). Ad hoc coordinates (requests with arbitrary latitude and longitude) are not persisted;
they keep the cache only path and their today is marked partial. Redis stays as the hot cache
in front of the API; the table is the record behind the worker.

## Consequences

Data volume is small (13 locations x 8 slots x 2 kinds per day). A retention job prunes
samples older than 90 days. The first day after deployment still shows a partial today; the
response says so (`partial`, `observed_samples`, `forecast_samples`). The roadmap item
"weather history" is absorbed by this decision.
