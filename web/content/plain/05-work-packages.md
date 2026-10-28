# 05 Work packages

Status: reviewed against 00 to 04, 2026-10-27.

The work is cut as it would be for a team of three (backend, web, platform). It runs in two
tracks:

- **Track A** builds the whole system locally, production-shaped. That means docker compose
  for development, and kind with the real Helm chart as the production rehearsal.
- **Track B** puts the same chart on a public server.

One person follows the same order.

Columns:

- **Kind** = what the package is for:
  - `brief`: required by the brief;
  - `prod`: production readiness;
  - `extra`: beyond the brief;
  - `site`: the case study site.
- **Size:** S under half a day, M about a day, L more.
- **Done when** = the acceptance checks of 01-requirements that must pass.

## Definition of done (every package)

1. The acceptance checks named in "Done when" pass as automated tests (unit, API or
   integration). The requirement id is in the test name.
2. ruff, mypy and the test suite are green in CI.
3. 03-data-model and 04-api match the code where the package touched them. An ADR is updated
   or added when a decision changed.
4. The package runs in `docker compose`. From L2 on, it also runs in kind through the chart.
5. The commit message names the package id.

## Local track (L): run everything on the laptop

| Id | Package | Kind | Size | Depends on | Done when |
|---|---|---|---|---|---|
| L1 | `docker compose` for the whole stack | prod | S | B1, W1 | One command starts the stack |
| L2 | kind cluster with the chart | prod | M | P5 | `make kind-up` installs everything |
| L3 | Production rehearsal checklist in 06-operations | prod | S | L2, P3 | N5.2, N5.3 rehearsed locally and recorded |

- **L1:**
  - Package: api, worker, beat, web, PostgreSQL, Redis; `.env.example`.
  - A mock upstream mode with recorded payloads runs when no API key is set.
  - Make targets: `make up`, `make test`, `make seed`, `make demo`.
  - Done when also: `/api/docs` and the site answer; tests run against the compose database.
- **L2:**
  - Package: `values-local.yaml`, CloudNativePG operator, ingress-nginx on localhost, migrate
    job, probes, resources.
  - Done when also: Q4 (rolling update with migrate job) rehearsed locally.
- **L3:** the checklist covers backup to a local MinIO, restore drill, rollback, and secrets
  created by `make secrets`.

## Backend (B)

| Id | Package | Kind | Size | Depends on | Done when |
|---|---|---|---|---|---|
| B1 | Django project skeleton | brief | M | | `/api/docs` serves the schema; N6.1 (401/403); A16 setting readable |
| B2 | Weather adapter and samples | brief | L | B1 | W1.1 to W1.5, W4.1 to W4.7 |
| B3 | Daily summary and forecast endpoint | brief | M | B2 | W2.1 to W2.6, W3.1 to W3.5 |
| B4 | Locations | brief | M | B2 | L1.1 to L1.6, L2.1 to L2.4 |
| B5 | Brackets | brief | M | B3, B4 | L3.1 to L3.6, L4.1 to L4.5 |
| B6 | Catalogue | brief | L | B4 | P1.1 to P1.7, P2.1 to P2.6, P4.1 to P4.4 |
| B7 | Departures | brief | M | B6 | P3.1 to P3.6 |
| B8 | Bookable search | brief | M | B7 | P5.1 to P5.7; N3.1 (`assertNumQueries`) |
| B9 | Booking | extra | L | B7 | P6.1 to P6.7, P4.5, N6.2 |
| B10 | Extras on the search | extra | S | B8, B9, B3 | N4.1 to N4.5, N4.7 |
| B11 | History and lifecycle | prod | M | B6 | N2.5, L1.6, P1.7, P2.2, P2.6, P3.6, P6.7; schema test (N2.7) |
| B12 | Operations status and demo | prod, site | S | B9, B2 | N5.5, A17, N6.7 |
| B13 | Hardening and quality gates | prod | M | B2, B9 | N6.3, N6.4, N6.6, W4.3 (Q8); N3.3 |

- **B1:**
  - settings by environment;
  - custom user with `role` and `partner_id`;
  - DRF with token auth, drf-spectacular;
  - RFC 7807 handler with the problem types of 04 §1;
  - `/healthz` and `/readyz`;
  - pagination and stable ordering defaults;
  - settings table (`bracket_edges`, `agency_timezone`, `sample_retention_days`);
  - Dockerfile (multi-stage, non-root, arm64 + amd64).
- **B2:**
  - Upstream client with timeouts, bounded retries with jitter, and a circuit breaker (a
    switch that stops calls to a failing upstream).
  - Budget split: refresh share, ad hoc share, 80 % cap, minute and month counters.
  - Ad hoc cache in Redis with stale fallback and 503 path.
  - `WeatherSample` upsert (newest wins, observation beats forecast).
  - `RefreshRun`.
  - Refresh tasks: scheduled with spread and adaptive interval, on create, manual.
  - Retention.
  - `/weather/current`.
  - Done when also: R1 and R2 as tests with a mocked upstream; one live smoke test (skipped
    without a key). The "visible in the operations status" clauses of W4.2 and W4.5 close
    with B12.
- **B3:**
  - `summarize_day`: mean, min, max to one decimal; daytime slots; significant weather order;
    cloudy on tie; `unknown`.
  - Local day by slot start with IANA zones.
  - `today` plus `days` with `partial` and sample counts.
  - Done when also: a table test with the edge cases (no daytime slot, DST day, tie, unmapped
    code).
- **B4:**
  - model: IANA zone derived offline when omitted, `active`, soft delete;
  - idempotent seed of the thirteen capitals with cited coordinates;
  - CRUD with delete guard (409 listing destinations);
  - admin;
  - refresh on create.
- **B5:**
  - half-open open-ended edges from the settings table;
  - `no_data` group;
  - `observed_at` and `stale` per location;
  - counts;
  - fixed and quantile modes with the shrink rule;
  - bracket-edges endpoint with attribution.
- **B6:**
  - `DestinationType` reference list;
  - `Destination`: danger 0 to 3, `active`, unique per location, delete guard;
  - `Package`: price per traveller, currency, duration, ordered destinations via
    `PackageDestination`, `active`, draft rule;
  - derived danger with label;
  - CRUD, admin.
- **B7:**
  - model with `status`;
  - capacity floor at confirmed seats;
  - `ends_on`;
  - CRUD;
  - cancel instead of delete when bookings exist;
  - past departures kept.
- **B8:**
  - input rules (dates, span, danger, unknown parameters);
  - one query with derived danger and remaining seats;
  - agency-zone today;
  - stable order, pagination;
  - second query for matching departures;
  - indexes;
  - `docs/plans/bookable.md` with EXPLAIN.
- **B9:**
  - `Traveller` (risk appetite, partner ownership);
  - `Partner` (`is_demo`);
  - `Booking` with `select_for_update`, seat bounds;
  - idempotency per creating user, with replay and mismatch;
  - price and danger snapshots;
  - idempotent cancel with `cancelled_by`;
  - partner scope (404 for other partners' rows);
  - travellers and partners endpoints, bookings list.
  - Done when also: concurrency test (Q3, 100 runs); two-partner isolation test (Q10).
- **B10:**
  - `traveller` (risk appetite as ceiling, 400 without one);
  - `type`, `max_price`;
  - `min_forecast_avg` with the "conditions now" note;
  - extras only narrow.
- **B11:**
  - `django-pghistory` on the ten tracked tables, with actor and request context;
  - "as of" read helper;
  - soft-delete manager;
  - danger-change attribution.
- **B12:**
  - `/ops/status` from `RefreshRun`, counters and breaker state;
  - demo partner and user;
  - demo data command (destinations, three packages, departures over ninety days,
    travellers);
  - nightly demo reset task.
  - Done when also: `make demo` and `make demo-reset`.
- **B13:**
  - pinned dependencies with a scanner in CI;
  - bandit;
  - rate limiting per token on ad hoc weather, with headers;
  - CORS for the site origin;
  - structured JSON logs with request id, user and partner;
  - OpenTelemetry hooks.

## Web (W)

| Id | Package | Kind | Size | Depends on | Done when |
|---|---|---|---|---|---|
| W1 | Next.js App Router skeleton | site | S | | Served at `/`; builds in CI |
| W2 | Overview and Decisions pages | site | M | W1 | 02 §0 and the ADR index readable on the site; every diagram renders (N1.5) |
| W3 | Live demo | site | L | B5, B8, B9, B10 | A visitor completes search, forecast and booking |
| W4 | API page, Plan page, Requirements and Domain pages | site | S | W2 | Pages reachable from the layout |
| W5 | Operations page from `/ops/status` | site | S | B12 | Live numbers match the API |
| W6 | Walkthrough | site | M | W2, W3, W5 | The ten minute path runs end to end |

- **W1:** shadcn/ui, seven sections in the layout, demo partner token from the environment,
  Dockerfile (multi-stage, non-root).
- **W2:**
  - render `docs/` and `adr/` from the repository at build time;
  - Mermaid flowcharts rendered client side;
  - arc42 sections navigable.
- **W3:**
  - locations on a map (lightweight library, no heavy GIS), coloured by bracket with the
    `no_data` group;
  - forecast panel on click (`today` plus `days`, `partial` shown);
  - bookable search form with the extras;
  - booking and sold-out flow as the demo partner.
  - Done when also: a 409 is shown when a departure sells out.
- **W4:** the API page embeds Swagger UI. The Plan page renders this file and 07-roadmap.
- **W5:** the page shows last run, calls against shares, breaker, cache hit ratio, sample
  count, versions. It has a refresh button for `ops`.
- **W6:** full screen, keyboard driven sections following 08-walkthrough. It pulls content
  from the other pages.

## Platform (P), Track B

| Id | Package | Kind | Size | Depends on | Done when |
|---|---|---|---|---|---|
| P1 | Terraform (hcloud): CAX21 ARM server | prod | M | | `kubectl get nodes` from the laptop; state in a private backend |
| P2 | Ingress and certificates | prod | S | P1 | A hello page over HTTPS with a valid certificate; risk 5 of 02 §11 retired |
| P3 | PostgreSQL | prod | M | P1 | `psql` connects; a backup object exists; restore drill recorded with duration (N5.3) |
| P4 | Redis deployment, image pull secret for ghcr, application secrets via `make secrets` | prod | S | P1 | `redis-cli ping` from a pod; pods pull private images |
| P5 | Helm chart | prod | L | B1, W1 | `helm install` on kind (L2) and on k3s; `helm rollback` works |
| P6 | CI/CD | prod | M | P5 | A commit on main is live in minutes; Q4 holds on the server |
| P7 | Observability stack | prod | M | P5, B13 | Operations page can link a dashboard; node memory under budget (02 §7.2) |
| P8 | Quick public URL before the domain (dropped 2026-10-28) | prod | S | P2 or P5 | Not needed while P2 holds |

- **P1:**
  - firewall (22 from operator IPs, 80, 443);
  - data volume;
  - cloud-init installing k3s with Traefik disabled;
  - kubeconfig retrieval.
- **P2:**
  - ingress-nginx;
  - cert-manager with a Let's Encrypt staging issuer first, then production;
  - DNS A record `travel-agency.<domain>` in Cloudflare (DNS only, no proxy), set by hand
    once P1 prints the address.
- **P3:**
  - CloudNativePG operator;
  - one instance cluster on the volume;
  - nightly base backup and WAL to Hetzner Object Storage, 14 day retention;
  - fallback to a plain chart if not clean within the first working day (ADR 0007).
- **P5:**
  - api (2 replicas), worker, beat, web;
  - migrate pre-upgrade job;
  - Redis, CNPG `Cluster`, ingress, probes;
  - requests and limits of 02 §7.2;
  - `values-local.yaml`, `values-hetzner.yaml`, `values-azure.yaml` (documented profile).
- **P6:**
  - ruff, mypy, pytest with PostgreSQL and Redis services;
  - squawk on migrations, dependency scan;
  - buildx arm64 + amd64, push to ghcr with SHA tags;
  - `helm upgrade` with a deploy kubeconfig;
  - smoke test on `/readyz` and one bookable query;
  - prune old images.
- **P7:** Prometheus and Grafana (kube-prometheus-stack) with RED dashboards and the budget
  and breaker gauges. Optional, last.
- **P8:**
  - Why dropped: the domain is in hand, and P2 serves the final name directly.
  - The plan was an sslip.io name on the Hetzner IP with cert-manager, or a single-image
    deploy of `api` plus `web` on a hosted service.

## Critical path and minimum deliverable

Track A order:

1. B1 and W1 together, then L1.
2. Then B2, B3, B4, B5 (weather, summaries, locations, brackets: W and L requirements
   complete).
3. Then B6, B7, B8 (catalogue, departures, the required search: P requirements complete).
   **The brief is now fulfilled locally.**
4. Then P5 and L2 (the chart on kind: production-shaped locally), B11, B12, B9, B10, B13, W2
   to W6.

Track B can start any time after P5 exists. It needs only a Hetzner token and, for the final
URL, a domain:

- P1, P2, P3, P4 in one sitting, then P6;
- P7 only if time allows;
- P8 is dropped.

Minimum deliverable: B1 to B8 running through L1 and L2 with W1 to W3. That is the brief,
locally and production-shaped, with a live demo.

Everything after that is additive. It can be cut in reverse order: P7, P8, W6, W5, B13, B10.

## Team mapping

- Backend engineer: B1 to B13 and L1.
- Web engineer: W1 to W6.
- Platform engineer: P1 to P8, L2, L3 and the chart.

Hand-offs:

- B1 and W1 give P5 its images.
- B12 gives W5 its data.
- P2 gives W3 its public URL.

A single person follows the Track A order and takes Track B in one block.
