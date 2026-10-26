# 0002 Capacity belongs to a departure date, bookings take a row lock

Status: accepted (2026-10-27)
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

Bookable = an active package with a danger score, and a planned departure that starts inside
the requested range, on or after today in the agency's time zone, with remaining seats > 0
(P5, A3, A16). A booking is at least one seat and at most the remaining seats, carries an
idempotency key unique per caller, and keeps the price and danger at booking time; cancelling
frees the seats and keeps the record. Capacity cannot be lowered below confirmed seats; a
departure with bookings is cancelled, not deleted (P3, P6). The bookable query joins
departures and aggregates bookings; indexes on `departure.starts_on` and
`booking(departure_id, status)`. A concurrency test with two parallel bookings for the last
seat is part of the suite.
