# 01a Functional requirements

Status: draft, 2026-10-26. Written by the rules in [01-requirements.md](01-requirements.md)
section 2. Identifiers: W weather, L locations and brackets, P packages. Assumptions (A) and
facts (F) referenced here are defined in 01-requirements.md and 01b.

## Weather

### W1 Current weather

- **Statement.** For a latitude and longitude, the system shall return the current temperature and condition, together with the time of observation and whether the value is live or stored.
- **Rationale.** The brief asks for the current weather of a given location.
- **Acceptance.**
  1. Valid coordinates are answered within one second on a warm system.
  2. Invalid coordinates (out of range, missing, not numeric) are rejected with a problem detail and no upstream call.
  3. During an upstream outage the last known value is returned and marked as stored or stale; the endpoint never answers 5xx because of the upstream.
- **Satisfied by.** ADR 0005 (cache, stale fallback); 04-api §Weather; tests in `weather/tests/`.

### W2 Daily forecast

- **Statement.** For a latitude and longitude, the system shall return a forecast for the next five days, each day with an average temperature and a condition label.
- **Rationale.** The brief asks for a five day forecast with average temperature and condition.
- **Acceptance.**
  1. Five days are returned, starting tomorrow in the location's local calendar; today is returned as a separate item.
  2. Each day's values are computed from every slot that falls on that local day; a day with incomplete data is marked as partial and states how many samples it used.
  3. The response states the time zone used and when the data was obtained.
  4. For a known location, today is complete once the system has run for a day (F1, ADR 0012).
- **Satisfied by.** ADR 0012 (persisted samples), ADR 0013 (summary rules, time); A11, A12, A13; 04-api §Weather.

### W3 Derived daily values

- **Statement.** The system shall derive daily temperature values and a daily condition itself from the slot data the upstream provides.
- **Rationale.** F1: the free tier has no daily endpoint; the brief wants daily values anyway.
- **Acceptance.**
  1. Daily temperature is reported as average, minimum and maximum over the day's slots.
  2. The daily condition is chosen from the daytime slots; significant weather (thunderstorm, rain, snow, fog) takes precedence over cloudy and clear; otherwise the most frequent wins.
  3. Upstream condition codes map to a closed set of labels; unknown codes map to a defined fallback, never to an error.
  4. A table test fixes the rules and their edge cases: no daytime slot, a daylight saving day with 7 or 9 slots, ties.
- **Satisfied by.** ADR 0013; A12.

### W4 Independence from the upstream

- **Statement.** The system shall stay responsive and inside the upstream's usage limits regardless of the upstream's latency, availability or the number of locations.
- **Rationale.** F2 and F3: the upstream is rate limited and outside our control; the brief asks for performance and stability.
- **Acceptance.**
  1. No request for a known location waits on the upstream.
  2. Upstream calls per minute stay below the limit at the configured refresh rate and location count; the budget used is observable.
  3. An upstream outage produces no 5xx from the weather endpoints and is visible in the operations status.
  4. Repeated upstream failures stop further calls for a cooling period and resume automatically.
- **Satisfied by.** ADR 0005 (scheduled refresh, cache, circuit breaker), ADR 0012; 06-operations.

## Locations and temperature brackets

### L1 Manageable location list

- **Statement.** Operations shall create, read, update and delete locations (name, country, coordinates, time zone) without developer help.
- **Rationale.** The brief: "the list of locations should be manageable".
- **Acceptance.**
  1. All four operations are available through the API to the `ops` role and through the admin.
  2. Coordinates and time zone are validated on write (ranges, valid IANA name).
  3. A deleted location disappears from listings and brackets but keeps its history and its weather samples.
- **Satisfied by.** ADR 0001 (Django admin and DRF); 04-api §Locations; 00-domain §5 (roles).

### L2 Initial data

- **Statement.** A fresh installation shall contain the capitals of South America as locations.
- **Rationale.** The brief: the list is initially filled with the capitals of South America.
- **Acceptance.**
  1. After migrations and seed, the capitals are listed with coordinates and IANA time zones.
  2. The Bolivia choice (Sucre, with La Paz as a second location) and the French Guiana choice are documented (A5).
  3. Running the seed twice changes nothing.
- **Satisfied by.** 03-data-model §Seed data; A5.

### L3 Grouping by temperature

- **Statement.** The system shall return the locations grouped by their current temperature bracket, stating the bracket edges used and when the temperatures were read.
- **Rationale.** The brief asks for the list grouped by temperature bracket.
- **Acceptance.**
  1. Every active location appears in exactly one bracket.
  2. The response carries the edges, the mode used and the refresh time of the temperatures.
  3. Serving the response triggers no upstream call.
- **Satisfied by.** ADR 0004 (brackets), ADR 0005 (refresh); 04-api §Locations.

### L4 Bracket tuning

- **Statement.** Bracket edges shall be adjustable so that the distribution is reasonable and, when wanted, no bracket is empty.
- **Rationale.** The brief: "feel free to tweak the temperature ranges so each bracket has at least one location".
- **Acceptance.**
  1. Edges are configurable by operations and validated (ascending, no gaps).
  2. A mode exists that guarantees non empty brackets by deriving edges from the data.
  3. In fixed mode an empty bracket is returned empty, never hidden (A4).
- **Satisfied by.** ADR 0004; A4.

## Tour packages

### P1 Package

- **Statement.** The system shall store tour packages with name, price, description, duration and a set of destinations.
- **Rationale.** The brief lists name, price, description and destinations; duration is added by A10 so that an end date exists.
- **Acceptance.**
  1. CRUD by the `ops` role through API and admin.
  2. Price is a decimal with an ISO currency code, never a float (A7).
  3. A package without destinations can be saved as a draft but is never bookable.
- **Satisfied by.** 03-data-model; A7, A10; 04-api §Catalogue.

### P2 Destination

- **Statement.** The system shall store destinations, each linked to one location, with a type and a danger score.
- **Rationale.** The brief: destinations link to a location, have a type and a danger score.
- **Acceptance.**
  1. Danger is an integer on the fixed scale 0 to 3 (A6); other values are rejected.
  2. A destination may belong to several packages; a location may have several destinations.
  3. Type is a closed set that operations can extend without a deployment.
- **Satisfied by.** ADR 0003; 03-data-model; A6.

### P3 Dated availability with capacity

- **Statement.** A package shall be offered on several dates, each with its own capacity, and the system shall never sell more seats than a date has.
- **Rationale.** The brief: multiple dates and limited capacity; A2 places the capacity on the date, A3 defines bookable.
- **Acceptance.**
  1. Each departure shows its capacity and remaining seats.
  2. Two concurrent bookings of the last seat yield exactly one success and one conflict response.
  3. A retried booking request with the same idempotency key does not book twice.
  4. A cancelled booking frees its seats and remains on record.
- **Satisfied by.** ADR 0002 (departure, row lock, idempotency); 04-api §Bookings.

### P4 Package danger

- **Statement.** A package's danger score shall equal the highest danger score among its destinations at all times.
- **Rationale.** The brief: the danger score of a package is the greatest one of its destinations.
- **Acceptance.**
  1. Changing a destination's danger changes every package containing it on the next read; no stale value is served.
  2. A package's danger is part of its API representation.
- **Satisfied by.** ADR 0003 (derived in the query).

### P5 Bookable packages search

- **Statement.** Given two dates and a danger score, the system shall return the bookable packages with their data.
- **Rationale.** The brief's required endpoint; A1 (at most), A3 (bookable), A10 (departure date) resolve its open readings.
- **Acceptance.**
  1. A package is returned when at least one of its departures starts inside the inclusive range, lies in the future and has seats left, and the package's danger does not exceed the given score.
  2. Exact danger match is available on request.
  3. Each result carries the package data and the matching departures with start date, end date and remaining seats.
  4. Results are paginated and the query stays index backed as data grows (EXPLAIN documented).
- **Satisfied by.** ADR 0002, 0003, 0011; A1, A3, A10; 04-api §Bookable search.
