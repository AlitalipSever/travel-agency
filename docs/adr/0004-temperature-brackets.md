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

Edges live in a settings table with validation (ascending, no gaps). The grouping reads
temperatures from the cache written by the refresh job (0005); it never calls upstream.
