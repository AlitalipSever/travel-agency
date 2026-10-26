# 01 Requirements

Status: draft, 2026-10-26. The brief, the writing rules, the requirements (W weather, L
locations, P packages, N non functional, F facts), the assumptions that close the brief's gaps,
the deliberate exclusions and the questions for the client.

## 1. The brief in one paragraph

A travel agency wants a system to manage its business. The backend exposes weather data from
OpenWeatherMap (free tier) for given coordinates, keeps a manageable list of locations that is
grouped by temperature bracket, and models the agency's product: tour packages with a name,
price, description, a set of destinations, several available dates and limited capacity.
Destinations link to a location, have a type (adventure, cultural, ...) and a danger score.
A package's danger score is the highest of its destinations. One endpoint must return all
bookable packages between two dates for a given danger score. Deliverables: a concise
architecture overview aligned with a Python, Django, PostgreSQL, Redis and cloud stack, the
application itself (fetch and process, clean model, performance, stability, maintainability),
suggested extra features, and a presentation of reasoning and trade-offs.

## 2. How requirements are written

The form follows the spirit of ISO/IEC/IEEE 29148 (requirements engineering), not its full
process. Each requirement is written to have these properties:

| Property | Meaning | How this document does it |
|---|---|---|
| Necessary | Traceable to the brief or to a fact about the environment | Rationale names the brief, an assumption (A) or a fact (F) |
| Solution free | Says what and why, never how | No framework, cache, queue or timing value inside a requirement; those live in ADRs and design documents |
| Unambiguous | One reading | Gaps in the brief are closed by a numbered assumption in section 3, not by silence |
| Verifiable | A check exists that passes or fails | Acceptance names the observable behaviour or the measurement |
| Traceable | Linked both ways to design and tests | Identifier (W, L, P, N) and a Satisfied by line; every ADR carries an Addresses line back |
| Singular | One requirement per item | Compound needs are split (for example W3 and W4) |

Template of one item:

> **Id Short name.** The system shall ... Rationale: ... Acceptance: ... Satisfied by: ...

Facts about the environment that shape the requirements are listed separately in 2.5; they
are constraints, not requirements. Non functional expectations (2.4) are measured by the
quality scenarios in 02 §10.2.

### 2.1 Weather

#### W1 Current weather

- **Statement.** For a latitude and longitude, the system shall return the current
  temperature (degrees Celsius) and condition, together with the time of observation and
  whether the value is live, cached or stale.
- **Rationale.** The brief asks for the current weather of a given location; A14 fixes the
  units.
- **Acceptance.**
  1. A known location, or a coordinate asked recently, is answered from stored data with p95
     latency under 100 ms.
  2. A coordinate asked for the first time is answered with p95 latency under 1.5 s including
     the upstream call.
  3. Invalid coordinates (out of range, missing, not numeric) are rejected with a problem
     detail and cause no upstream call.
  4. When the upstream is down, slow or rate limiting and a stored value exists, that value is
     returned and marked stale with its age; no 5xx.
  5. When the upstream is unavailable and no stored value exists, the response is 503 with a
     problem detail and a Retry-After header; no made-up data, no empty 200.
- **Satisfied by.** ADR 0005 (cache, stale fallback, unavailability); 04-api §Weather; tests
  in `weather/tests/`.

#### W2 Daily forecast

- **Statement.** For a latitude and longitude, the system shall return a forecast for the next
  five days, each day with average, minimum and maximum temperature (degrees Celsius) and a
  condition label from the closed set of W3.
- **Rationale.** The brief asks for a five day forecast with average temperature and
  condition; minimum and maximum follow common practice (ADR 0013).
- **Acceptance.**
  1. Five days are returned, starting tomorrow in the location's local calendar; today is
     reported separately from the five.
  2. A slot belongs to the local day in which it starts; each day's values are computed from
     all slots of that day.
  3. A day is marked partial when any of its slots is missing (today's past hours for an ad
     hoc coordinate, the last day cut by the 120 hour window, a gap in the upstream data) and
     states how many observed and forecast samples it used.
  4. For a known location, today is not partial once samples exist for all of its past slots
     (ADR 0012). A location added during the day stays partial until the next local day; an
     ad hoc coordinate is always partial for today.
  5. The response states the time zone used and when the data was obtained.
  6. Latency, invalid input and upstream unavailability behave as in W1 (1 to 5).
- **Satisfied by.** ADR 0012, ADR 0013; A11, A12, A13, A14; 04-api §Weather.

#### W3 Derived daily values

- **Statement.** The system shall derive each day's temperature values and condition label
  itself from the slot data the upstream provides, applying the same rules to observed and
  forecast slots.
- **Rationale.** F1: the free tier has no daily endpoint; the brief wants daily values.
- **Acceptance.**
  1. Daily temperature is reported as average, minimum and maximum over the day's slots, to
     one decimal.
  2. Daytime slots are those the upstream marks as day; without that mark, 06:00 to 18:00
     local.
  3. The daily condition is chosen from the daytime slots: significant weather first, in the
     order thunderstorm, rain, snow, fog; otherwise the most frequent of cloudy and clear,
     cloudy on a tie. With no daytime slot, all slots are used.
  4. Upstream condition codes map to the closed set thunderstorm, rain, snow, fog, cloudy,
     clear, unknown; an unmapped code yields unknown, never an error.
  5. A table test fixes the rules and the edge cases: no daytime slot, a daylight saving day
     with 7 or 9 slots, ties, an unmapped code.
- **Satisfied by.** ADR 0013; A12; `weather/summary.py` and its table test.

#### W4 Independence from the upstream

- **Statement.** The system shall stay responsive and inside the upstream's usage limits
  whatever the upstream's latency or availability, and shall protect that budget from its own
  callers.
- **Rationale.** F2 and F3; the brief asks for performance and stability.
- **Acceptance.**
  1. No request for a known location waits on the upstream.
  2. The scheduled refresh spreads its calls over the interval and keeps the total, together
     with ad hoc calls, under 80 % of the per minute limit; when the location count would
     exceed that, the interval lengthens rather than the limit being crossed. Monthly usage
     stays under the monthly limit. Both counters are observable.
  3. Ad hoc coordinate requests are rate limited per caller and draw from a reserved share of
     the budget; exhausting that share answers 429 with Retry-After and does not slow the
     scheduled refresh.
  4. A failing upstream call for one location does not stop the refresh of the others; the
     failed location keeps its last values.
  5. During an upstream outage, known locations are served from stored data (no 5xx), ad hoc
     requests follow W1 (4 and 5), and the outage is visible in the operations status.
  6. After repeated failures the system stops calling the upstream for a cooling period and
     resumes automatically; while open, ad hoc requests fail fast instead of waiting for
     timeouts.
  7. No request is held longer than the configured upstream timeout; the W1 latency targets
     hold.
- **Satisfied by.** ADR 0005 (refresh, budget, circuit breaker), ADR 0012; 04-api §Operations;
  06-operations.

### 2.2 Locations and temperature brackets

#### L1 Manageable location list

- **Statement.** Operations shall create, read, update, deactivate and delete locations (name,
  country, coordinates, time zone) without developer help.
- **Rationale.** The brief: "the list of locations should be manageable".
- **Acceptance.**
  1. All operations are available through the API to the `ops` role and through the admin;
     every role can read locations.
  2. Writes are validated: coordinate ranges, a valid IANA time zone, and uniqueness of name
     and country. If the time zone is omitted it is derived from the coordinates (offline
     lookup) and can be overridden.
  3. A deactivated location leaves listings, brackets and the scheduled refresh but keeps its
     data and can be reactivated.
  4. A location with active destinations cannot be deleted; the response names them. A deleted
     location disappears from listings and brackets but keeps its history and its weather
     samples.
  5. Creating a location triggers an immediate weather refresh; data is available within one
     minute. A later coordinate correction takes effect at the next scheduled refresh.
  6. Every write is recorded with actor and time.
- **Satisfied by.** ADR 0001; 04-api §Locations; 00-domain §5; 02 §8 (audit).

#### L2 Initial data

- **Statement.** A fresh installation shall contain the capitals of South America as active
  locations.
- **Rationale.** The brief: the list is initially filled with the capitals of South America.
- **Acceptance.**
  1. A fresh installation lists the twelve capitals of the sovereign states of South America
     plus La Paz as Bolivia's seat of government, each with coordinates, ISO 3166-1 alpha-2
     country code and IANA time zone. Cayenne is not included: French Guiana is a region of
     France, not a country (A5).
  2. The seed file states the source of its coordinates.
  3. Seeding is idempotent and never overwrites a row that operations have edited.
  4. Demo data for the catalogue (destinations, packages, departures) is a separate, optional
     step and is not part of this requirement.
- **Satisfied by.** 03-data-model §Seed data; A5.

#### L3 Grouping by temperature

- **Statement.** The system shall return the active locations grouped by their current
  temperature bracket, stating the bracket edges used and when each temperature was read.
- **Rationale.** The brief asks for the list grouped by temperature bracket.
- **Acceptance.**
  1. Brackets are half-open intervals, lower edge included, upper excluded, with an open
     bracket below the lowest edge and another at or above the highest, so that every
     temperature falls into exactly one bracket.
  2. Every active location with a temperature appears in exactly one bracket; a location
     without one (not yet refreshed, or never fetched) appears in a separate "no data" group
     with the reason, never hidden.
  3. Each location carries its temperature and the time it was observed; a value older than a
     configured age is marked stale but still placed.
  4. In fixed mode an empty bracket is returned with zero locations (A4).
  5. The response carries the edges, the mode used and the time of the last refresh; brackets
     are ordered by temperature ascending and so are the locations inside.
  6. Serving the response triggers no upstream call and meets the W1 (1) latency target.
- **Satisfied by.** ADR 0004, ADR 0005, ADR 0012; A4; 04-api §Locations.

#### L4 Bracket tuning

- **Statement.** Bracket edges shall be adjustable by operations so that the distribution is
  reasonable and, when wanted, no bracket is empty.
- **Rationale.** The brief: "feel free to tweak the temperature ranges so each bracket has at
  least one location".
- **Acceptance.**
  1. Operations set the fixed edges as a strictly ascending list of one to ten numbers; the
     brackets follow from it (L3.1), so no other validation is needed.
  2. A change takes effect on the next read; no refresh or recomputation is required, and it
     is recorded with actor and time.
  3. The default edges are documented together with the distribution they produced on the
     seed data on a stated date.
  4. Quantile mode derives edges from the current temperatures for a requested number of
     brackets (default four) so that none is empty; when fewer distinct temperatures exist
     than brackets requested, the number of brackets shrinks and the response says so.
     Quantile edges are reported to one decimal.
  5. The response reports the number of locations per bracket so the distribution can be
     judged at a glance; in fixed mode an empty bracket is returned empty (A4).
- **Satisfied by.** ADR 0004; A4; 04-api §Locations.

### 2.3 Tour packages

#### P1 Package

- **Statement.** Operations shall manage tour packages with name, price, description, duration
  and an ordered list of destinations.
- **Rationale.** The brief lists name, price, description and "a series of destinations";
  duration is added by A10 so that an end date exists; the price is per traveller (A15).
- **Acceptance.**
  1. CRUD by the `ops` role through API and admin; every role can read active packages.
  2. Price is a decimal with an ISO currency code, never a float (A7), and is the price per
     traveller; changing it does not change existing bookings, which keep the price they were
     made at.
  3. Destinations keep the order operations gave them; the same destination appears at most
     once in a package.
  4. Duration is at least one day; the description is short text (at most 2,000 characters).
  5. A package is bookable only when it is active, has at least one destination and at least
     one bookable departure (P3); otherwise it is a draft or inactive and never appears in the
     bookable search.
  6. A package whose departures have bookings cannot be deleted; it is deactivated instead,
     and its bookings stay visible.
  7. Every write is recorded with actor and time.
- **Satisfied by.** 03-data-model; A7, A10, A15; 04-api §Catalogue; 02 §8 (audit).

#### P2 Destination

- **Statement.** The system shall store destinations, each linked to one location, with a type and a danger score.
- **Rationale.** The brief: destinations link to a location, have a type and a danger score.
- **Acceptance.**
  1. Danger is an integer on the fixed scale 0 to 3 (A6); other values are rejected.
  2. A destination may belong to several packages; a location may have several destinations.
  3. Type is a closed set that operations can extend without a deployment.
- **Satisfied by.** ADR 0003; 03-data-model; A6.

#### P3 Dated availability with capacity

- **Statement.** A package shall be offered on several dates, each with its own capacity, and the system shall never sell more seats than a date has.
- **Rationale.** The brief: multiple dates and limited capacity; A2 places the capacity on the date, A3 defines bookable.
- **Acceptance.**
  1. Each departure shows its capacity and remaining seats.
  2. Two concurrent bookings of the last seat yield exactly one success and one conflict response.
  3. A retried booking request with the same idempotency key does not book twice.
  4. A cancelled booking frees its seats and remains on record.
- **Satisfied by.** ADR 0002 (departure, row lock, idempotency); 04-api §Bookings.

#### P4 Package danger

- **Statement.** A package's danger score shall equal the highest danger score among its destinations at all times.
- **Rationale.** The brief: the danger score of a package is the greatest one of its destinations.
- **Acceptance.**
  1. Changing a destination's danger changes every package containing it on the next read; no stale value is served.
  2. A package's danger is part of its API representation.
- **Satisfied by.** ADR 0003 (derived in the query).

#### P5 Bookable packages search

- **Statement.** Given two dates and a danger score, the system shall return the bookable packages with their data.
- **Rationale.** The brief's required endpoint; A1 (at most), A3 (bookable), A10 (departure date) resolve its open readings.
- **Acceptance.**
  1. A package is returned when at least one of its departures starts inside the inclusive range, lies in the future and has seats left, and the package's danger does not exceed the given score.
  2. Exact danger match is available on request.
  3. Each result carries the package data and the matching departures with start date, end date and remaining seats.
  4. Results are paginated and the query stays index backed as data grows (EXPLAIN documented).
- **Satisfied by.** ADR 0002, 0003, 0011; A1, A3, A10; 04-api §Bookable search.

### 2.4 Non functional requirements

#### N1 Architecture overview

- **Statement.** A concise architecture overview aligned with a Python, Django, PostgreSQL, Redis and cloud stack shall describe data flow, structure and the main design choices.
- **Rationale.** The brief's first deliverable.
- **Acceptance.**
  1. arc42 sections 1 to 12 present (arc42-checklist.md), C4 context and container diagrams, every significant choice in an ADR.
- **Satisfied by.** 02-architecture, adr/.

#### N2 Clean data model

- **Statement.** The data model shall be readable in one sitting, with explicit constraints and no duplicated derived values without a stated reason.
- **Rationale.** The brief: "model the data in a clean and professional way".
- **Acceptance.**
  1. ER diagram, constraints and indexes documented; derived values (package danger, remaining seats, end date) computed, not stored, unless an ADR says otherwise.
- **Satisfied by.** 03-data-model; ADR 0002, 0003, 0011.

#### N3 Performance, stability, maintainability

- **Statement.** The system shall meet the quality scenarios defined for it and follow the structure rules of the repository.
- **Rationale.** The brief names the three words; scenarios make them measurable.
- **Acceptance.**
  1. Quality scenarios Q1 to Q7 in 02 §10.2 pass (latency unchanged in an upstream outage, zero overbookings, zero failed requests during a deploy, restore under 30 minutes, bounded change effort).
  2. Files under 200 lines, thin views, services per app, tests at the seams (AGENTS.md).
- **Satisfied by.** 02 §10.2; AGENTS.md; CI.

#### N4 Extra features

- **Statement.** Extra features and filters that add value for the client shall be proposed and, where the effort is small, implemented.
- **Rationale.** The brief's third deliverable.
- **Acceptance.**
  1. Every proposed extra is tied to a job of an actor in 00-domain §3.
  2. Implemented extras are tested and documented like the required features; proposed ones state what they would take.
- **Satisfied by.** 04-api (extras); 07-roadmap.

#### N5 Production ready (our reading of the brief's goal line)

- **Statement.** The system shall run for real, with deployment, rollback, backups, health checks and secret handling in place.
- **Rationale.** The brief's goal line says production ready; we read it as running in production, and mark that as our reading.
- **Acceptance.**
  1. A public URL serves the API and the site over HTTPS.
  2. Deploy and rollback are single commands; a restore drill has been run; secrets are not in git.
- **Satisfied by.** ADR 0006, 0007, 0009; 06-operations.

### 2.5 Facts about the environment (constraints, not requirements)

- **F1** The free tier forecast endpoint returns 40 three hour slots from the next full slot after now, plus one current observation. No daily endpoint, no history, nothing beyond 120 hours. One Call 3.0 offers daily values but needs a paid subscription; the brief says free tier only.
- **F2** The free tier allows 60 calls per minute and about one million per month.
- **F3** The upstream is outside our control: it may be slow, down or rate limiting.
- **F4** Slot timestamps are UTC; the forecast response carries the location's offset. Chile and Paraguay observe daylight saving time; most other South American countries do not.

## 3. Assumptions (gaps in the brief, how we fill them)

| # | Gap | Assumption | ADR |
|---|---|---|---|
| A1 | "For a given danger score": equal or at most | At most: the client asks "nothing more dangerous than medium". Exact match offered as a query flag | 0003 |
| A2 | Capacity per package or per date | Per departure date. A sold out date does not block other dates | 0002 |
| A3 | What "bookable" means | Departure date inside the range, in the future, and seats remaining | 0002 |
| A4 | Temperature brackets fixed or dynamic | Configurable fixed edges, default tuned to the seed; a quantile mode as an option. In fixed mode a bracket may be empty in some seasons; the response returns it empty rather than hiding it | 0004 |
| A5 | Which cities count as capitals | The twelve sovereign states' capitals; Bolivia gives Sucre (constitutional) and La Paz (seat of government); Cayenne excluded, French Guiana is not a country | 03-data-model |
| A6 | Danger score scale | Integer 0 to 3: none, low, medium, high | 0003 |
| A7 | Currency of price | One currency per package, default EUR, stored as decimal plus ISO code | 03-data-model |
| A8 | Who calls the API | Operations, sales and finance of the agency, and partner agencies' systems; travellers never call the API directly in this iteration. Token auth, roles `ops`, `sales`, `partner`, `finance` | 00-domain §5 |
| A9 | Framework | Django + DRF as the brief's stack implies, not FastAPI | 0001 |
| A10 | "Between two dates": the departure inside the range, or the whole trip | The departure date inside the range (industry convention, the data the brief gives); packages get `duration_days` so each departure also reports `ends_on` | 0011 |
| A11 | Does "next five days" include today, and how are cut days reported | Response has `today` and `days` (five, from tomorrow). Today is complete for known locations once samples exist (0012), partial for ad hoc coordinates; a day cut by the 120 hour window is marked `partial`; every day reports its sample counts | 0013 |
| A12 | What the daily "condition" is | Daytime slots, most significant weather first (thunderstorm, rain, snow, fog, cloudy, clear), most frequent as tie break; upstream codes mapped to that closed set | 0013 |
| A13 | Which day is "a day" | The location's local calendar day: timestamps stored in UTC, each location carries an IANA zone, summaries convert in code and state the zone | 0013 |
| A14 | Units | Metric: degrees Celsius, m/s, hPa; other unit systems in the roadmap | 04-api |
| A15 | What the price is | Per traveller, the same for every departure of the package; a booking keeps the price at booking time; per-departure pricing in the roadmap | 03-data-model |

## 4. Out of scope, deliberately

Payments, user registration and password flows, multi tenancy, a traveller facing booking
front end, internationalisation. Each is named in 07-roadmap.md with what it would take.

## 5. Questions I would ask the client first

Listed with the working assumption behind each in [00-domain.md](00-domain.md) section 7.
None blocks the work: every answer that differs from the assumption is a small, localised
change, and the assumptions above say where.
