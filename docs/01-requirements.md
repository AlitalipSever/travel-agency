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
     one bookable departure (P3, P6); otherwise it is a draft or inactive and never appears in the
     bookable search.
  6. A package whose departures have bookings cannot be deleted; it is deactivated instead,
     and its bookings stay visible.
  7. Every write is recorded with actor and time.
- **Satisfied by.** 03-data-model; A7, A10, A15; 04-api §Catalogue; 02 §8 (audit).

#### P2 Destination

- **Statement.** Operations shall manage destinations, each linked to one location, with one
  type and a danger score.
- **Rationale.** The brief: destinations link to a location, are one of several types and
  carry a danger score that the agency keeps adjusting.
- **Acceptance.**
  1. CRUD by the `ops` role through API and admin; every role can read destinations.
  2. Danger is an integer on the fixed scale 0 to 3 (A6); other values are rejected. A change
     of danger is recorded with actor and time and raises the `DestinationDangerChanged` event
     once events exist (ADR 0008).
  3. Types are a reference list that operations maintain (initial values adventure, cultural,
     nature, urban, beach); a destination has exactly one type.
  4. A destination may belong to several packages; a location may have several destinations;
     name is unique within a location.
  5. A destination used by any package cannot be deleted; the response names the packages. An
     inactive destination cannot be added to new packages but stays in the packages that
     contain it, danger included.
  6. Every write is recorded with actor and time.
- **Satisfied by.** ADR 0003; 03-data-model; A6; 00-domain §6; 04-api §Catalogue.

#### P3 Departures and capacity

- **Statement.** Operations shall offer a package on several dates, each departure with its own
  capacity, and the system shall never let confirmed seats exceed that capacity.
- **Rationale.** The brief: multiple dates and limited capacity; A2 puts the capacity on the
  date, A3 defines bookable.
- **Acceptance.**
  1. CRUD of departures (start date, capacity) by the `ops` role; one departure per package and
     date; capacity at least one.
  2. Each departure reports capacity, confirmed seats and remaining seats, and its end date
     from the package's duration (ADR 0011).
  3. Capacity cannot be lowered below the confirmed seats; the response states the number.
  4. A departure with bookings cannot be deleted; it can be cancelled, which marks its bookings
     as cancelled by the agency and removes it from the bookable search. A departure without
     bookings can be deleted.
  5. A departure in the past is not bookable and stays on record.
  6. Every write is recorded with actor and time; a departure reaching zero remaining seats
     raises `DepartureSoldOut` once events exist.
- **Satisfied by.** ADR 0002, ADR 0011; 03-data-model; 04-api §Catalogue.

#### P4 Package danger

- **Statement.** A package's danger score shall equal the highest danger score among its
  destinations at all times, inactive destinations included.
- **Rationale.** The brief: the danger score of a package is the greatest one of its
  destinations.
- **Acceptance.**
  1. Changing a destination's danger changes every package containing it on the next read; no
     stale value is served.
  2. A package with no destinations has no danger score (null), is a draft (P1.5) and never
     appears in the bookable search.
  3. The package representation carries the score and its label (none, low, medium, high).
  4. Deriving the score does not break the latency target of the bookable search (P5); the
     query plan is documented.
  5. A booking records the package's danger at booking time, so later changes are visible as
     a difference.
- **Satisfied by.** ADR 0003 (derived in the query); 03-data-model; 04-api §Catalogue.

#### P5 Bookable packages search

- **Statement.** Given two dates and a danger score, the system shall return the bookable
  packages with their data.
- **Rationale.** The brief's required endpoint; A1 (at most), A3 (bookable), A10 (departure
  date) resolve its open readings.
- **Acceptance.**
  1. Inputs: `from` and `to` as ISO dates with `from <= to` and a span of at most 366 days,
     and a danger score 0 to 3; anything else is a 400 problem detail.
  2. A package is returned when it is active, has a danger score, that score does not exceed
     the given one, and at least one of its planned departures starts inside the inclusive
     range, on or after today in the agency's time zone, with seats left.
  3. Exact danger match is available on request (`danger_mode=exact`).
  4. Each result carries the package data (P1, P4) and only the matching departures, each with
     start date, end date, capacity and remaining seats.
  5. Results are ordered by earliest matching departure, then package name, then id, and
     paginated; the order is stable across pages.
  6. Additional filters (traveller risk appetite instead of danger, type, maximum price,
     weather) only narrow this result, never widen it (N4).
  7. Latency: p95 under 100 ms on the seed data and under 300 ms with thousands of packages
     and tens of thousands of departures; the query plan is documented.
- **Satisfied by.** ADR 0002, 0003, 0011; A1, A3, A10; 04-api §Bookable search.

#### P6 Booking (extra feature that gives capacity its meaning)

- **Statement.** Sales, partners and operations shall book seats on a departure for a traveller
  and cancel such bookings, without ever overbooking.
- **Rationale.** Not demanded by the brief, but "bookable" and "limited capacity" have no
  observable meaning without it; it is the first extra (N4) and the job of sales and partners
  (00-domain §3).
- **Acceptance.**
  1. A booking names a departure, a traveller and a number of seats (at least one, at most the
     remaining seats); otherwise 409 with the remaining count.
  2. Two concurrent bookings of the last seat yield exactly one success and one conflict.
  3. A repeated request with the same idempotency key returns the original booking and books
     nothing new; the key is unique per caller.
  4. The booking keeps the price per traveller and currency at booking time (P1.2).
  5. Cancelling frees the seats and keeps the record; cancelling twice returns the same result
     without error.
  6. A partner sees and cancels only its own bookings; sales and operations see all; finance
     reads all.
  7. Every booking and cancellation is recorded with actor and time and raises
     `BookingConfirmed` or `BookingCancelled` once events exist.
- **Satisfied by.** ADR 0002, ADR 0008; 00-domain §5; 04-api §Bookings.

### 2.4 Non functional requirements

#### N1 Architecture overview

- **Statement.** A concise architecture overview, aligned with a Python, Django, PostgreSQL,
  Redis and cloud stack, shall describe the data flow, the structure and the main design
  choices.
- **Rationale.** The brief's first deliverable.
- **Acceptance.**
  1. A one-page summary exists that stands on its own: what the system does, the container
     diagram, the two main data flows (weather in, bookable search out), the three main
     decisions with their trade-offs, and the stack table; under 600 words.
  2. Every stack element is named with its role and the ADR behind it: Django and DRF (0001),
     PostgreSQL (0007), Redis (0005), Kubernetes and cloud (0006, including the Azure values
     profile).
  3. The long form follows arc42 sections 1 to 12 (arc42-checklist.md) with C4 context and
     container diagrams; the data flows are drawn now, sequence detail follows the code.
  4. Every significant choice is an ADR with options and consequences; the summary names which
     three are the main ones.
  5. All diagrams render on GitHub and on the case study site.
- **Satisfied by.** 02-architecture §0 (summary) and §3 to §7; adr/; the site's Overview page.

#### N2 Clean data model

- **Statement.** The data model shall be normalised, explicit about its constraints, consistent
  in naming and types, and small enough to read in one sitting.
- **Rationale.** The brief: "model the data in a clean and professional way". The rules below
  follow the standards and practices tracked in 03-data-model §"Standards and practices
  followed" (each with where it applies and how it is checked).
- **Acceptance.**
  1. Integrity rules live in the database (foreign keys, unique constraints, CHECKs for danger
     0 to 3, capacity >= 1, duration >= 1, coordinate ranges, booking seats >= 1) and are
     mirrored, not replaced, by application validation.
  2. Tables are in third normal form; derived values (package danger, remaining seats, end
     date) are computed, not stored. The two snapshots on a booking (price and danger at
     booking time) are deliberate copies that keep the booking record immutable, and are
     documented as such.
  3. Naming and types follow one convention: UUID keys, `timestamptz` columns end in `_at`,
     `date` columns in `_on`, money as `numeric(12,2)` with an ISO 4217 code (never `money`
     or floats), `text` with CHECKs instead of `varchar(n)`, closed sets as CHECK constraints,
     operations-managed sets as reference tables, lower case snake_case identifiers.
  4. Every table carries `created_at` and `updated_at`; soft-deleted tables carry `deleted_at`.
  5. Change history of the catalogue, departures, bookings, locations and bracket settings is
     kept by database triggers in per-table history tables with the acting user and request
     (ADR 0014), so that any row can be read "as of" a time; application code cannot forget it.
  6. Every index is justified by a named query (P5, L3, W2) and its plan is documented; no
     speculative indexes.
  7. The ER diagram matches the schema: it is generated from the models or checked by a test
     that compares table and column names.
  8. At most twelve application tables (history tables excluded), none above fifteen columns;
     the ER diagram fits on one page.
- **Satisfied by.** 03-data-model; ADR 0002, 0003, 0011, 0014; migrations;
  `core/tests/test_schema.py`.

#### N3 Performance, stability, maintainability

- **Statement.** The system shall respond within its latency targets, keep working when its
  dependencies fail, and stay easy to change.
- **Rationale.** The brief names the three; ISO 25010 calls them time behaviour, reliability
  and maintainability; the scenarios in 02 §10.2 make them measurable.
- **Acceptance.**
  1. Performance: the latency targets of W1 and P5 hold on the seed data and are checked by a
     timed test; list endpoints run a bounded number of queries (no N+1), asserted in tests.
  2. Stability: Q1 (upstream outage), Q3 (last seat), Q4 (deploy) and Q5 (restore) pass;
     liveness and readiness probes are in place.
  3. Maintainability: Q6 and Q7 (change scenarios) hold; CI runs lint, type check and tests on
     every push and blocks a merge on failure; code files stay under 200 lines with thin views
     and services per app (AGENTS.md).
- **Satisfied by.** 02 §10.2; AGENTS.md; CI; tests.

#### N4 Extra features

- **Statement.** Extra features and filters that add value for the client shall be proposed
  and, where the effort is small, implemented; each one shall come from a job of a named actor.
- **Rationale.** The brief's third deliverable; 00-domain §3 lists the jobs so that extras are
  answers to needs, not decoration.
- **Acceptance.**
  1. Implemented: booking with capacity, concurrency safety and idempotency (P6; job of sales
     and partners).
  2. Implemented: suitability by traveller. The bookable search accepts `traveller={id}` and
     uses that traveller's risk appetite as the "at most" danger; a traveller without a
     recorded appetite is a 400 problem detail naming the field (job of sales: "nothing too
     risky for this traveller").
  3. Implemented: weather aware filter. `min_forecast_avg=<°C>` keeps packages whose
     destinations' locations all have a five day average temperature at or above the value.
     It describes conditions now, not on the departure date, and the response says so (job of
     marketing: "destinations above 25 °C this week").
  4. Implemented: `type=` and `max_price=` filters on the bookable search and the package list
     (job of sales).
  5. Every extra only narrows the required result (P5.6); with no extra parameter the required
     behaviour is unchanged.
  6. Proposed only, each with what it would take, in 07-roadmap: holds and waiting lists,
     cancellation fees, notifications on danger change and departure cancellation, traveller
     self-service, per-departure pricing, booking cut-off, weather history comparison.
  7. Implemented extras are tested and documented like the required features.
- **Satisfied by.** 04-api §Bookable search, §Bookings; 07-roadmap; 00-domain §3.

#### N5 Production ready (our reading of the brief's goal line)

- **Statement.** The system shall run for real: reachable on the public internet, deployable
  and recoverable from code, with its secrets, health and backups handled.
- **Rationale.** The brief's goal line says "production-ready application"; we read it as
  running in production and mark that as our reading, not the brief's demand.
- **Acceptance.**
  1. A public URL serves the API, its documentation and the case study site over HTTPS with a
     valid certificate.
  2. The infrastructure is created from code (Terraform) and the application deployed by one
     command or by CI on every push to main; rollback is one command.
  3. Database backups run nightly to object storage and a restore drill has been performed and
     recorded in 06-operations with its duration.
  4. No secret is in git; secrets are injected at deploy time and can be rotated by replacing
     them and restarting.
  5. Liveness and readiness probes gate traffic; an operations status endpoint and page show
     cache, refresh, budget and breaker state.
  6. A runbook (06-operations) covers deploy, rollback, backups, secrets, health and the first
     things to look at when something is wrong; the monthly cost is listed.
- **Satisfied by.** ADR 0006, 0007, 0009; 06-operations; 04-api §Operations.

### 2.5 Facts about the environment (constraints, not requirements)

- **F1** The free tier forecast endpoint returns 40 three hour slots from the next full slot
  after now, plus one current observation. No daily endpoint, no history, nothing beyond 120
  hours. One Call 3.0 offers daily values but needs a paid subscription; the brief says free
  tier only.
- **F2** The free tier allows 60 calls per minute and about one million per month.
- **F3** The upstream is outside our control: it may be slow, down or rate limiting.
- **F4** Slot timestamps are UTC; the forecast response carries the location's current offset.
  Daylight saving rules change: Chile observes it, Brazil abolished it in 2019 and Paraguay
  moved to permanent summer time in 2024. The IANA database carries these changes, which is
  why zone names, not offsets, are stored, and why the runtime's tz data must be kept current.
- **F5** Our own API is an upstream for the agency's front end and for partner systems whose
  traffic we do not control; the upstream budget must be protected from them (W4.3).

## 3. Assumptions (gaps in the brief, how we fill them)

| # | Gap | Assumption | Decided in |
|---|---|---|---|
| A1 | "For a given danger score": equal or at most | At most: the client asks "nothing more dangerous than medium". Exact match offered as a query flag | 0003 |
| A2 | Capacity per package or per date | Per departure date. A sold out date does not block other dates | 0002 |
| A3 | What "bookable" means | An active package with a danger score, and a planned departure that starts inside the range, on or after today in the agency's time zone (A16), with seats remaining | 0002; P5 |
| A4 | Temperature brackets fixed or dynamic | Configurable fixed edges, default [10, 20, 25, 30] tuned to the seed; a quantile mode as an option. In fixed mode a bracket may be empty in some seasons; the response returns it empty rather than hiding it | 0004 |
| A5 | Which cities count as capitals | The twelve sovereign states' capitals; Bolivia gives Sucre (constitutional) and La Paz (seat of government); Cayenne excluded, French Guiana is not a country | 03-data-model |
| A6 | Danger score scale | Integer 0 to 3: none, low, medium, high | 0003 |
| A7 | Currency of price | One currency per package, default EUR, stored as decimal plus ISO code | 03-data-model |
| A8 | Who calls the API | Operations, sales and finance of the agency, and partner agencies' systems; travellers never call the API directly in this iteration. Token auth, roles `ops`, `sales`, `partner`, `finance`; a partner sees only its own bookings | 00-domain §5 |
| A9 | Framework | Django + DRF as the brief's stack implies, not FastAPI | 0001 |
| A10 | "Between two dates": the departure inside the range, or the whole trip | The departure date inside the range (industry convention, the data the brief gives); packages get `duration_days` so each departure also reports `ends_on` | 0011 |
| A11 | Does "next five days" include today, and how are cut days reported | Response has `today` and `days` (five, from tomorrow). Today is complete for known locations once samples exist (0012), partial for ad hoc coordinates; a day cut by the 120 hour window is marked `partial`; every day reports its sample counts | 0013 |
| A12 | What the daily "condition" is | Daytime slots; significant weather first in the order thunderstorm, rain, snow, fog; else the most frequent of cloudy and clear, cloudy on a tie; upstream codes mapped to a closed set with `unknown` as fallback | 0013; W3 |
| A13 | Which day is "a day" | The location's local calendar day: timestamps stored in UTC, each location carries an IANA zone, summaries convert in code and state the zone | 0013 |
| A14 | Units | Metric: degrees Celsius, m/s, hPa; other unit systems in the roadmap | 04-api |
| A15 | What the price is | Per traveller, the same for every departure of the package; a booking keeps the price at booking time; per-departure pricing in the roadmap | 03-data-model |
| A16 | Which "today" decides whether a departure is still bookable | The agency's time zone, a setting operations can change; a departure starting today is still bookable (cut-off in the roadmap) | P5; 02 §8 |

## 4. Out of scope, deliberately

Payments and refunds, user registration and password flows, traveller self-service, multi
tenancy, internationalisation, event streaming and high availability. The full list, each with
why it is left out and what it would take, is 07-roadmap.md; it also holds the policy items a
real agency would ask about next (holds, fees, cut-off, notifications).

## 5. Questions I would ask the client first

Listed with the working assumption behind each in [00-domain.md](00-domain.md) section 7;
every row there points at the assumption (A) or requirement it would change. None blocks the
work: an answer that differs from the assumption is a small, localised change.
