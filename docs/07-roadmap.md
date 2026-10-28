# 07 Roadmap

Status: reviewed against 01 to 06, 2026-10-27. Four lists, kept honest: what is done, what
was left out on purpose, what would come next, and what would make the design change.

## 1. Done

Filled in as packages close (ids from 05-work-packages). A row is added when the package's
acceptance checks pass in CI.

| Package | Closed | Acceptance checks | Note |
|---|---|---|---|
| B1 Django skeleton | 2026-10-27 (PR #1) | `/api/docs` serves the schema; N6.1 401 tested; A16 setting readable | 403 per role lands with the permission matrix (B9) |
| L1 docker compose | 2026-10-27 (PR #2) | `make up`, `/readyz`, `make test` against the compose database | The site service joins when W1 lands |
| B2 Weather adapter and samples | 2026-10-27 (PR #3) | W1.1 to W1.5, W4.1 to W4.7 with a mocked upstream; live smoke test against OpenWeatherMap | Operations-status clauses of W4.2 and W4.5 close with B12 |
| B3 Daily summary and forecast | 2026-10-27 (PR #4) | W2.1 to W2.6, W3.1 to W3.5; table tests for DST days, ties, no daytime slot, unmapped codes | Expected slots counted from aligned UTC slot starts (ADR 0013) |
| B4 Locations | 2026-10-27 (PR #5) | L1.1 to L1.5, L2.1 to L2.4; 403 matrix for sales and partner | L1.6 attribution lands with B11 |
| B5 Brackets | 2026-10-27 (PR #6) | L3.1 to L3.6, L4.1 to L4.5; latest observations in one query | Quantile mode rounds temperatures to one decimal so no bracket is empty |
| B6 Catalogue | 2026-10-27 (PR #7) | P1.1 to P1.4, P2.1 to P2.5, P4.1 to P4.3; package list in three queries | Danger derived in the query (ADR 0003); write field is `destination_ids` |
| B7 Departures | 2026-10-27 (PR #8) | P3.1 to P3.5, P1.6; cancel idempotent under the row lock | Booking tables created here (model only) so seats are real; rules and endpoints with B9 |
| B8 Bookable search | 2026-10-27 (PR #9) | P5.1 to P5.5, N3.1 (five queries per page); P5.7 measured in `docs/plans/bookable.md` | One partial index took query 1 from 1,340 ms to 21 ms on 20,000 departures |
| B12 (part) Operations status | 2026-10-28 | N5.5: `/api/v1/ops/status` with last run, shares, breaker, ad hoc cache counters, sample count, versions | Demo seed landed earlier (PR #10); nightly demo reset still open |
| W1 Site skeleton | 2026-10-28 (PR #11) | Served at `/`; builds in CI; demo token server side through the proxy route (ADR 0015) | Seven sections; Spectral theme |
| W2 Documents and decisions | 2026-10-28 (PR #13, #19) | N1.5: every diagram of 02 renders; documents and ADRs from the repository at build time | Mermaid client side |
| W3 Live demo | 2026-10-28 (PR #14, #19) | Brackets map, forecast panel, bookable search, booking with the 200 replay, the 409 and cancel | Map from world-atlas, no tiles |
| W3 (add) Current weather by coordinate | 2026-10-28 | Map click or typed coordinate calls `GET /weather/current?lat=&lon=` through the proxy; source badge shows sample / live / cached / stale; 429 and 503 bodies shown as returned | No API change: the ad hoc path (ADR 0005) existed, the site now exposes it |
| W4 API browser and Plan | 2026-10-28 (PR #15, #19) | OpenAPI document read from the API; 05 and 07 rendered | Swagger UI linked on the API origin (frame denied) |
| W5 Operations page | 2026-10-28 (PR #17) | Live numbers match `/ops/status`, read every 30 s | Shares drawn on the thermal scale |
| W6 Walkthrough | 2026-10-28 (PR #18, #20) | The nine steps of 08 as a keyboard driven deck with a ten minute clock | Pulls the demo, status and summary into the steps |
| B9 Booking | 2026-10-28 (PR #12) | P6.1 to P6.6, N6.2 with two partner tokens; P6.2 concurrency test, 20 rounds of two threads on the last seat | P6.7 attribution lands with B11; `/partners` endpoint deferred (admin creates partners) |
| P1 Server and k3s | 2026-10-28 (PR #25) | `kubectl get nodes` from the laptop; firewall 22 and 6443 from the operator only; data volume at `/mnt/data` | Terraform, one CAX21, pinned k3s, Traefik disabled; state and token local |
| P2 Ingress and certificates | 2026-10-28 | Hello page at `https://travel-agency.asever.dev` with a Let's Encrypt certificate; staging issuer rehearsed first; risk 5 of 02 §11 retired | ingress-nginx and cert-manager by Helm (`make bootstrap`); the chart takes the host in P5 |
| P6a CI | 2026-10-28 (PR #27) | ruff, format, mypy, pytest with PostgreSQL and Redis services, eslint and tsc on every pull request; multi-arch images to ghcr on `main` | Squawk, dependency scan and the deploy step (P6b) still open |
| P5 Helm chart | 2026-10-28 | `helm upgrade --install` on the Hetzner node: migrate hook job, api (2 replicas, probes on `/readyz` and `/healthz`), worker, beat (Recreate), web, Redis, built-in PostgreSQL on the data volume, Ingress with the P2 certificate; ten revisions on day one, `helm rollback` available | Q4 rehearsed: the probes' `Host` header and the SSL redirect belong to the ingress (06 §8); images pushed from the laptop (`make images-push`) |
| B12 (rest) Demo in the cluster | 2026-10-28 | `make k8s-demo` seeds partner, users, packages and bookings; `make demo-token` stores the demo partner token; the site's demo flow runs against the live API | Nightly demo reset task still open |
| W7 Agency site | 2026-10-28 | The site reads as a travel agency (Andes & Coast): home with the bookable search, destinations with live temperatures and forecasts, tours with adventure levels, dated departures and the booking dialog; everything about the engineering sits behind one "Case study" menu; plain English throughout | Photos are AI-made (Gemini) and say so in the footer; the demo page keeps the engineer's view of the same calls |

## 2. Deliberately left out

Each item with why it is out and what it would take; the brief's scope (01 §4) and the
decisions (adr/) are the reasons.

| Item | Why | What it would take |
|---|---|---|
| CloudNativePG (P3) | The chart ships one PostgreSQL StatefulSet on the Hetzner volume (ADR 0007 fallback, taken on day one for time); no operator, no automated backup yet | `postgres.mode: cnpg` in the chart rendering a `Cluster`, the operator chart, Object Storage credentials, the restore drill of 06 §5 |
| CI deploy (P6b) and kind (L2) | Releases went out from the laptop with the same `helm upgrade` CI would run; kind was not needed to reach the server | A deploy kubeconfig as a GitHub secret, the smoke test and rollback step of 06 §2; `values-local.yaml` on a kind cluster |
| Event streaming (Kafka or an outbox) | No requirement needs fan-out yet; the refresh job and bookings are tasks and transactions; the events are named (00-domain §6) and the booking service is written behind an interface (ADR 0008) | Outbox table, a producer in the booking service, a consumer for notifications; Redpanda or Event Hubs in the chart |
| High availability | One server is enough for the brief; HA is a platform step, not an application change (02 §11 risk 1) | Second node, PostgreSQL with two instances (one setting in CloudNativePG), api replicas spread by anti-affinity, beat on a lease |
| Payments and refunds | Out of the brief; large surface and compliance | A payment provider adapter, a payment state on bookings, refund rules tied to cancellation fees |
| Traveller self-service | The brief asks for a system that runs the agency; travellers book through staff and partners (00-domain §2) | A `traveller` role with registration, login and password flows, own-bookings scope, and a front end |
| GDPR access and erasure flows | Personal data is minimal (name, email) and erasure is an operations task today (02 §2 Legal) | Export and erasure endpoints that anonymise the traveller while keeping booking counts; retention rules on history tables |
| Multi tenancy | One agency in the brief | Tenant id on every table, row level security, per-tenant settings |
| Internationalisation | One agency, one language; API payloads are language neutral | Translated labels (conditions, types) and localised formats behind `Accept-Language` |
| Booking cut-off before departure | Whether a tour departing today is still bookable is the agency's policy; today it is (A16) | A cut-off in hours per package or globally, applied in the bookable rule and at booking time |
| Holds, waiting lists, cancellation fees | A real agency's first questions after booking works; each is a policy the client must set | A hold status with expiry on bookings, a waiting list per departure, a fee rule on cancellation |
| Notifying travellers of a cancelled departure or a raised danger | Needs a channel and a policy; the change is recorded and visible to sales (P2.2, P3.4) | A consumer of `DepartureCancelled` and `DestinationDangerChanged` that lists affected bookings and sends mail |
| Per-departure and seasonal pricing | One price per package is what the brief describes (A15) | A price on the departure overriding the package's, and a price history |
| Unit systems other than metric | Celsius is natural for the agency and its markets (A14) | A `units` query parameter converting at the edge |
| Precipitation probability in the daily label | A threshold is a judgement call (ADR 0013) | `pop` above a client-set threshold counts as rain |
| Analytics and reporting (warehouse, star schema) | The system is transactional; reporting on it would compete with bookings for locks | An ELT feed from the tables and history into a warehouse with `fact_booking` and `dim_date`, `dim_package`, `dim_location`, `dim_partner` |
| Managed cloud services for the demo | Cost and portability; an AKS profile is kept (ADR 0006) | Run `values-azure.yaml` with managed PostgreSQL and Redis |
| Webhooks or an event feed for partners | No partner asked; the API is pull based | Outbox first, then signed webhooks per partner |
| Bulk import of catalogue data | Operations manages a small catalogue by hand | CSV import with validation report |

## 3. Next two weeks, if this continued

In order of value to the client, each pointing at what it closes.

1. Second node, PostgreSQL replica and beat on a lease: retires risk 1 (02 §11).
2. Outbox and domain events for bookings, with a mail consumer for cancellations and danger
   changes: closes the two notification rows above.
3. Load test with k6 at the Q9 sizes; numbers recorded in 02 §10.2 and `docs/plans/`.
4. GDPR export and erasure endpoints; retention policy for history tables.
5. Booking cut-off and cancellation fees as settings, once the client states the policy.
6. "Same day last week" comparison on the brackets page from the persisted samples.
7. Contract tests against the OpenAPI schema and a generated TypeScript client for the site.
8. Precipitation probability in the condition rule behind a client-set threshold.

## 4. What would make the design change

| Signal | Change | Prepared by |
|---|---|---|
| Catalogue in the tens of thousands and the derived danger shows in query plans | Stored, trigger-maintained danger column | ADR 0003 names it as the next step |
| More than a few hundred locations | Paid upstream tier or a second provider behind the adapter | W4.2 adaptive interval buys time; Q7 isolates the adapter |
| Partners need their own prices or quotas | Partner-scoped price lists and quotas on departures | Partner already a first-class table |
| Travellers book themselves | Traveller role and identity flows | Traveller already a table; roles already a column |
| Reporting demand from finance | Warehouse feed (row above) | History tables carry the change stream |

## 5. How this grows with a larger team

Module boundaries follow the Django apps: `weather`, `locations`, `catalog`, `booking`, each
with its own models, services, tests and ADR section; the one-way dependency rule (02 §5.2)
keeps them separable. The first split into its own service would be the weather adapter,
whose load profile (scheduled, upstream bound) differs from the API's. The chart stays one;
values files multiply per environment. Ownership: one pair per app, a platform pair for the
chart, Terraform and CI, and the site with the backend pair that owns the API it demonstrates.
