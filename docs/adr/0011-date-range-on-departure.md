# 0011 The date range filter applies to the departure date

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: P1, P5; A10

## Context

The required endpoint returns bookable packages "between two given dates". A tour is not a
point in time but a span: it starts on a departure date and lasts a number of days. The brief
lists the package's fields (name, price, description, destinations, dates, capacity) but no
duration, so it gives no way to compute when a tour ends. "Between two dates" can therefore be
read as "departs inside the range" or as "the whole trip lies inside the range".

## Options

1. Filter on the departure date only. No new field needed for the filter; one indexed column;
   matches how tour operators and booking platforms expose "departure date from / to", with
   duration as a separate filter.
2. Filter on the whole trip: departure on or after `from`, and departure plus duration on or
   before `to`. Needs a duration per package and two conditions on a computed end date.
3. Option 1 by default with option 2 behind a query flag.

## Decision

Option 1. It follows the industry convention and the data the brief gives, and it builds
nothing nobody asked for. A `duration_days` field is still added to the package, not for the
filter but because a real agency knows and shows the length of a tour; the response carries
`starts_on` and the computed `ends_on` for every departure, so a consumer can apply a stricter
rule on its side if it wants to.

## Consequences

Package gains `duration_days` (positive integer, required, seeded). The bookable query filters
`departure.starts_on` between the two dates, inclusive. `ends_on = starts_on + duration_days
- 1` (a 7 day tour starting on the 8th ends on the 14th). If the client asks for the whole-trip
reading, it is one more condition in the query and a new ADR; the flag of option 3 was
considered and left out as unrequested.
