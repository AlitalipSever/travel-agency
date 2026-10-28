# 0002 Capacity belongs to a departure date, bookings take a row lock

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: P3, P5, P6; A2, A3

## Context

The brief says: "Each package can be available on multiple dates and have a limited capacity."

The sentence does not say whether capacity is one number per package or one per date.
"Bookable" has to mean something: it implies seats being used up.

## Options

1. Capacity on the package, dates as a list. This is simple. But either one sold out date
   blocks all dates, or capacity has no relation to dates at all.
2. A Departure row per package and date, with its own capacity. Bookings reference the
   departure. Remaining seats are computed from confirmed bookings.
3. Option 2 with a stored `remaining_seats` counter, updated on every booking.

## Decision

Option 2. A departure is the sellable unit, as in every real tour operator system.

Remaining seats are computed (capacity minus confirmed seats) inside a transaction. That
transaction locks the departure row (`select_for_update`), so two concurrent bookings cannot
oversell.

Idempotency keys make retried requests safe. (An idempotency key is a caller-chosen key that
lets the server recognise a repeated request and not apply it twice.)

A stored counter (option 3) is a later optimisation. It comes only if the aggregate shows up
in measurements.

## Consequences

**Bookable** means all of the following (P5, A3, A16):

- an active package with a danger score;
- a planned departure that starts inside the requested range;
- the departure starts on or after today, in the agency's time zone;
- remaining seats > 0.

**A booking:**

- is at least one seat and at most the remaining seats;
- carries an idempotency key, unique per caller;
- keeps the price and danger at booking time.

Cancelling frees the seats and keeps the record.

**Departures** (P3, P6):

- Capacity cannot be lowered below confirmed seats.
- A departure with bookings is cancelled, not deleted.

**Query and tests:**

- The bookable query joins departures and aggregates bookings.
- Indexes on `departure.starts_on` and `booking(departure_id, status)`.
- A concurrency test with two parallel bookings for the last seat is part of the suite.
