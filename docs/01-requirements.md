# 01 Requirements

Status: draft, 2026-10-26.

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

## 2. Requirements

### How requirements are written here

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
quality scenarios in 02b §10.2.

### 2.1 Weather

- **W1 Current weather.** For a latitude and longitude, the system shall return the current
  temperature and condition, with when it was observed and whether the value is live or
  stored. Rationale: the brief. Acceptance: valid coordinates answer within one second from a
  warm system; invalid coordinates are rejected with a problem detail; during an upstream
  outage the last known value is returned and marked as such. Satisfied by: ADR 0005; 04-api.
- **W2 Daily forecast.** For a latitude and longitude, the system shall return a forecast for
  the next five days, each day with an average temperature and a condition label. Rationale:
  the brief. Acceptance: five days returned; each day's values are computed from all slots of
  that local calendar day; a day with incomplete data is marked; the day boundary follows the
  location's time zone. Satisfied by: ADR 0012, 0013; A11, A12, A13; 04-api.
- **W3 Derived daily values.** The system shall derive daily values itself from the data the
  upstream provides (2.5, F1). Rationale: the free tier has no daily endpoint. Acceptance: a
  table test fixes the derivation rules (mean, min, max; condition selection) and their edge
  cases (no daytime slot, daylight saving day). Satisfied by: ADR 0013.
- **W4 Independence from the upstream.** The system shall stay responsive and inside the
  upstream's limits regardless of the upstream's latency, availability or the number of
  locations. Rationale: F2, F3. Acceptance: no request waits on the upstream for a known
  location; upstream calls per minute stay below the limit at the configured refresh rate; an
  upstream outage produces no 5xx from the weather endpoints. Satisfied by: ADR 0005, 0012.

### 2.2 Locations and temperature brackets

- **L1 Manageable location list.** Operations shall create, read, update and delete locations
  (name, country, coordinates, time zone) without developer help. Rationale: the brief
  ("manageable"). Acceptance: the four operations through the API and the admin; a deleted
  location disappears from listings but keeps its history. Satisfied by: ADR 0001; 04-api.
- **L2 Initial data.** The list shall start with the capitals of South America. Rationale: the
  brief. Acceptance: a fresh installation lists them with coordinates and time zones; the
  Bolivia choice is documented (A5). Satisfied by: 03-data-model (seed).
- **L3 Grouping by temperature.** The system shall return the locations grouped by their
  current temperature bracket, stating the bracket edges used and when the temperatures were
  read. Rationale: the brief. Acceptance: every active location appears in exactly one
  bracket; the response never triggers upstream calls. Satisfied by: ADR 0004, 0005; 04-api.
- **L4 Bracket tuning.** Bracket edges shall be adjustable so that the distribution is
  reasonable and, when wanted, no bracket is empty. Rationale: the brief. Acceptance: edges are
  configurable by operations; a mode exists that guarantees non empty brackets; in fixed mode
  an empty bracket is returned empty, not hidden. Satisfied by: ADR 0004; A4.

### 2.3 Tour packages

- **P1 Package.** The system shall store packages with name, price, description, duration and
  a set of destinations. Rationale: the brief (duration added, A10). Acceptance: CRUD by
  operations; price is a decimal with a currency code. Satisfied by: 03-data-model; A7.
- **P2 Destination.** The system shall store destinations, each linked to one location, with a
  type and a danger score. Rationale: the brief. Acceptance: danger is on a fixed scale (A6);
  a destination may belong to several packages. Satisfied by: ADR 0003; 03-data-model.
- **P3 Dated availability with capacity.** A package shall be offered on several dates, each
  with its own capacity, and the system shall never sell more seats than a date has.
  Rationale: the brief; A2, A3. Acceptance: two concurrent bookings of the last seat yield one
  success and one conflict; remaining seats are visible per date. Satisfied by: ADR 0002.
- **P4 Package danger.** A package's danger score shall equal the highest danger of its
  destinations, at all times. Rationale: the brief. Acceptance: changing a destination's
  danger changes every package that contains it on the next read. Satisfied by: ADR 0003.
- **P5 Bookable packages search.** Given two dates and a danger score, the system shall return
  the bookable packages with their data. Rationale: the brief. Acceptance: a package is
  returned when at least one of its departures starts inside the range, lies in the future
  and has seats left, and its danger does not exceed the given score (exact match available
  on request); results carry the matching departures with start, end and remaining seats.
  Satisfied by: ADR 0002, 0003, 0011; A1, A3, A10; 04-api.

### 2.4 Non functional

- **N1 Architecture overview.** A concise overview aligned with a Python, Django, PostgreSQL,
  Redis and cloud stack: data flow, structure, main choices. Satisfied by: 02-architecture,
  adr/.
- **N2 Clean data model.** Entities, relations and constraints that a reviewer can read in
  one sitting; derived values not duplicated without reason. Satisfied by: 03-data-model;
  ADR 0002, 0003.
- **N3 Performance, stability, maintainability.** Measured by the quality scenarios in
  02b §10.2 (latency unchanged during upstream outage, zero overbookings, zero failed requests
  during a deploy, restore under 30 minutes) and by the structure rules in AGENTS.md.
- **N4 Extra features.** Suggestions that add value for the client, implemented where the
  effort is small; each one tied to a job in 00-domain §3. Satisfied by: 04-api (extras),
  07-roadmap.
- **N5 Production ready (our reading of the brief's goal line).** The system runs for real,
  with deploy, rollback, backups, health and secrets handled. Satisfied by: ADR 0006, 0007,
  0009; 06-operations.

### 2.5 Facts about the environment (constraints, not requirements)

- **F1** The free tier forecast endpoint returns 40 three hour slots from the next full slot
  after now, plus one current observation. No daily endpoint, no history, nothing beyond 120
  hours. One Call 3.0 offers daily values but needs a paid subscription; the brief says free
  tier only.
- **F2** The free tier allows 60 calls per minute and about one million per month.
- **F3** The upstream is outside our control: it may be slow, down or rate limiting.
- **F4** Slot timestamps are UTC; the forecast response carries the location's offset. Chile
  and Paraguay observe daylight saving time; most other South American countries do not.

## 3. Assumptions (gaps in the brief, how we fill them)

| # | Gap | Assumption | ADR |
|---|---|---|---|
| A1 | "For a given danger score": equal or at most | At most: the client asks "nothing more dangerous than medium". Exact match offered as a query flag | 0003 |
| A2 | Capacity per package or per date | Per departure date. A sold out date does not block other dates | 0002 |
| A3 | What "bookable" means | Departure date inside the range, in the future, and seats remaining | 0002 |
| A4 | Temperature brackets fixed or dynamic | Configurable fixed edges, default tuned to the seed; a quantile mode as an option. In fixed mode a bracket may be empty in some seasons; the response returns it empty rather than hiding it | 0004 |
| A5 | Which capital for Bolivia | Sucre (constitutional); La Paz recorded as a second location | 03-data-model |
| A6 | Danger score scale | Integer 0 to 3: none, low, medium, high | 0003 |
| A7 | Currency of price | One currency per package, default EUR, stored as decimal plus ISO code | 03-data-model |
| A8 | Who calls the API | Operations, sales and finance of the agency, and partner agencies' systems; travellers never call the API directly in this iteration. Token auth, roles `ops`, `sales`, `partner`, `finance` | 00-domain §5 |
| A9 | Framework | Django + DRF as the brief's stack implies, not FastAPI | 0001 |
| A10 | "Between two dates": the departure inside the range, or the whole trip | The departure date inside the range (industry convention, the data the brief gives); packages get `duration_days` so each departure also reports `ends_on` | 0011 |
| A11 | Does "next five days" include today, and how are cut days reported | Response has `today` and `days` (five, from tomorrow). Today is complete for known locations once samples exist (0012), partial for ad hoc coordinates; a day cut by the 120 hour window is marked `partial`; every day reports its sample counts | 0013 |
| A12 | What the daily "condition" is | Daytime slots, most significant weather first (thunderstorm, rain, snow, fog, cloudy, clear), most frequent as tie break; upstream codes mapped to that closed set | 0013 |
| A13 | Which day is "a day" | The location's local calendar day: timestamps stored in UTC, each location carries an IANA zone, summaries convert in code and state the zone | 0013 |

## 4. Out of scope, deliberately

Payments, user registration and password flows, multi tenancy, a traveller facing booking
front end, internationalisation. Each is named in 07-roadmap.md with what it would take.

## 5. Questions I would ask the client first

Listed with the working assumption behind each in [00-domain.md](00-domain.md) section 7.
None blocks the work: every answer that differs from the assumption is a small, localised
change, and the assumptions above say where.
