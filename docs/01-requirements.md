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

## 2. Decomposition

### 2.1 Weather

- W1 Current weather for a latitude and longitude.
- W2 Five day forecast for a latitude and longitude: one row per day with average temperature
  and a condition label (sunny, cloudy, rain, ...).
- W3 The free tier forecast endpoint returns 3 hour slots (40 per 5 days, from the next full
  slot after now). Daily average and a daily condition are derived by us. One Call 3.0 would
  give daily values but needs a paid subscription; the brief says free tier only.
- W4 The upstream API is rate limited (60 calls per minute on the free tier) and may be slow or
  down. The system must stay responsive and inside the limit.

### 2.2 Locations and temperature brackets

- L1 A manageable list of locations (create, read, update, delete): name, country, latitude,
  longitude, IANA time zone (needed for local calendar days, A13).
- L2 Seeded with the capitals of South America.
- L3 An endpoint that returns the locations grouped by current temperature bracket.
- L4 Brackets may be tuned so that each bracket has at least one location and the distribution
  is reasonable.

### 2.3 Tour packages

- P1 TourPackage: name, price, description, a set of destinations.
- P2 Destination: linked to one location; has a type; has a danger score.
- P3 A package is available on several dates and has limited capacity.
- P4 Package danger score = max danger score of its destinations (derived).
- P5 Endpoint: bookable packages between two dates for a given danger score, with their data.
  The brief gives no tour duration; see A10.

### 2.4 Non functional

- N1 Architecture overview aligned with Python, Django, PostgreSQL, Redis, cloud.
- N2 Clean, professional data model.
- N3 Performance, stability, maintainability.
- N4 Extra features that add value for the client, suggested and where possible implemented.
- N5 Production ready: runs for real, with the operational basics in place.

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
| A8 | Who calls the API | Agency staff (write) and client applications (read); token auth, two roles | 04-api |
| A9 | Framework | Django + DRF as the brief's stack implies, not FastAPI | 0001 |
| A10 | "Between two dates": the departure inside the range, or the whole trip | The departure date inside the range (industry convention, the data the brief gives); packages get `duration_days` so each departure also reports `ends_on` | 0011 |
| A11 | Does "next five days" include today, and how are cut days reported | Response has `today` and `days` (five, from tomorrow). Today is complete for known locations once samples exist (0012), partial for ad hoc coordinates; a day cut by the 120 hour window is marked `partial`; every day reports its sample counts | 0013 |
| A12 | What the daily "condition" is | Daytime slots, most significant weather first (thunderstorm, rain, snow, fog, cloudy, clear), most frequent as tie break; upstream codes mapped to that closed set | 0013 |
| A13 | Which day is "a day" | The location's local calendar day: timestamps stored in UTC, each location carries an IANA zone, summaries convert in code and state the zone | 0013 |

## 4. Out of scope, deliberately

Payments, user registration and password flows, multi tenancy, a customer facing booking
front end, internationalisation. Each is named in 07-roadmap.md with what it would take.

## 5. Open questions for the client

None blocking. The assumptions above would be confirmed in the first review; each is a one line
change if the answer differs.
