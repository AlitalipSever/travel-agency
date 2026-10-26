# 01 Requirements

Status: draft, 2026-10-26. This file holds the brief, the writing rules, the index of all
requirement ids, the assumptions that close the brief's gaps, the deliberate exclusions and the
questions for the client. The requirements themselves are in
[01a (functional)](01a-requirements-functional.md) and
[01b (quality and facts)](01b-requirements-quality-and-facts.md).

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

Facts about the environment that shape the requirements are listed separately in 01b; they
are constraints, not requirements. Non functional expectations (2.4) are measured by the
quality scenarios in 02b §10.2.

### Index of requirements

| Id | Name | Where |
|---|---|---|
| W1 | Current weather | [01a](01a-requirements-functional.md) |
| W2 | Daily forecast | [01a](01a-requirements-functional.md) |
| W3 | Derived daily values | [01a](01a-requirements-functional.md) |
| W4 | Independence from the upstream | [01a](01a-requirements-functional.md) |
| L1 | Manageable location list | [01a](01a-requirements-functional.md) |
| L2 | Initial data | [01a](01a-requirements-functional.md) |
| L3 | Grouping by temperature | [01a](01a-requirements-functional.md) |
| L4 | Bracket tuning | [01a](01a-requirements-functional.md) |
| P1 | Package | [01a](01a-requirements-functional.md) |
| P2 | Destination | [01a](01a-requirements-functional.md) |
| P3 | Dated availability with capacity | [01a](01a-requirements-functional.md) |
| P4 | Package danger | [01a](01a-requirements-functional.md) |
| P5 | Bookable packages search | [01a](01a-requirements-functional.md) |
| N1 | Architecture overview | [01b](01b-requirements-quality-and-facts.md) |
| N2 | Clean data model | [01b](01b-requirements-quality-and-facts.md) |
| N3 | Performance, stability, maintainability | [01b](01b-requirements-quality-and-facts.md) |
| N4 | Extra features | [01b](01b-requirements-quality-and-facts.md) |
| N5 | Production ready (our reading of the brief's goal line) | [01b](01b-requirements-quality-and-facts.md) |
| F1 to F4 | Facts about the upstream and time zones | [01b](01b-requirements-quality-and-facts.md) |

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
