# 0004 Temperature brackets are configurable fixed edges, quantile mode optional

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: L3, L4; A4

## Context

Locations are listed grouped by current temperature bracket (0 to 10, 11 to 20 and so on).

The brief allows tuning the ranges, so that each bracket has at least one location and the
distribution is reasonable.

Thirteen capitals in one continent cluster around 10 to 30 °C, depending on season. Fixed
textbook edges leave brackets empty.

## Options

1. Hard coded edges: predictable, but breaks the "at least one per bracket" wish in some
   seasons.
2. Configurable fixed edges (a setting, editable by operations), with defaults tuned to the
   seed data.
3. Dynamic edges computed from the data (quantiles): never empty, but the edges move every
   refresh and are hard to communicate.

## Decision

Option 2 as the default. Option 3 sits behind a query parameter (`mode=quantile&buckets=4`).

A client wants stable, nameable brackets in its UI. The dynamic mode is offered for
exploration.

The response always returns the edges used, so the consumer never guesses.

## Consequences

**Edges and defaults**

- Edges live in a settings table as a strictly ascending list of one to ten numbers.
- The default is [10, 20, 25, 30]. Brackets: below 10, 10 to 20, 20 to 25, 25 to 30, 30 and
  above.
- The default was chosen for South American capitals. The distribution it produced on the
  seed data is recorded in the seed file on the day the system first ran.
- A change applies on the next read and is audited.

**Quantile mode**

- It takes a bracket count (default four).
- It derives edges from the current temperatures, to one decimal.
- When fewer distinct temperatures exist, it shrinks the count and says so in the response.

**Brackets**

- Brackets report their location count.
- Brackets are half-open: the lower edge is included, the upper excluded.
- There is an open bracket below the lowest edge and one at or above the highest. So every
  temperature lands in exactly one bracket.

**Locations and data**

- Locations without a temperature yet are returned in a separate "no data" group, with the
  reason.
- Each location carries its observed time, and a stale mark past a configured age.
- The grouping reads the latest observation per location from the samples of ADR 0012. It
  never calls upstream.
