# 0002 Capacity belongs to a departure date, bookings take a row lock

Status: proposed
Date: 2026-10-26
Addresses: P3, P5, P6; A2, A3

## Context

"Each package can be available on multiple dates and have a limited capacity." The sentence
does not say whether capacity is one number per package or one per date. "Bookable" has to
mean something; it implies seats being used up.

## Options

1. Capacity on the package, dates as a list: simple, but one sold out date blocks all dates,
   or capacity has no relation to dates at all.
2. A Departure row per package and date with its own capacity; bookings reference the
   departure; remaining seats are computed from confirmed bookings.
3. Option 2 with a stored `remaining_seats` counter updated on every booking.

## Decision

Option 2. A departure is the sellable unit, as in every real tour operator system. Remaining
seats are computed (capacity minus confirmed seats) inside a transaction that locks the
departure row (`select_for_update`), so two concurrent bookings cannot oversell. Idempotency
keys make retried requests safe. A stored counter (option 3) is a later optimisation, only
if the aggregate shows up in measurements.

## Consequences

Bookable = departure in the requested range, in the future, remaining seats > 0. The bookable
query joins departures and aggregates bookings; indexes on `departure.starts_on` and
`booking(departure_id, status)`. A concurrency test with two parallel bookings for the last
seat is part of the suite.
