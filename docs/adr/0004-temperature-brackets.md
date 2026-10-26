# 0004 Temperature brackets are configurable fixed edges, quantile mode optional

Status: proposed
Date: 2026-10-26
Addresses: L3, L4; A4

## Context

Locations are listed grouped by current temperature bracket (0 to 10, 11 to 20 and so on). The
brief allows tuning the ranges so that each bracket has at least one location and the
distribution is reasonable. Thirteen capitals in one continent cluster around 10 to 30 °C
depending on season; fixed textbook edges leave brackets empty.

## Options

1. Hard coded edges: predictable, breaks the "at least one per bracket" wish in some seasons.
2. Configurable fixed edges (a setting, editable by staff), defaults tuned to the seed data.
3. Dynamic edges computed from the data (quantiles): never empty, but edges move every refresh
   and are hard to communicate.

## Decision

Option 2 as the default, option 3 behind a query parameter (`mode=quantile&buckets=4`). A
client wants stable, nameable brackets in its UI; the dynamic mode is offered for exploration.
The response always returns the edges used, so the consumer never guesses.

## Consequences

Edges live in a settings table with validation (ascending, no gaps). Brackets are half-open
(lower edge included, upper excluded) with an open bracket below the lowest edge and one at or
above the highest, so every temperature lands in exactly one bracket. Locations without a
temperature yet are returned in a separate "no data" group with the reason. Each location
carries its observed time and a stale mark past a configured age. The grouping reads the
latest observation per location from the samples of ADR 0012; it never calls upstream.
