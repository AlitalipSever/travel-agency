# 05 Work packages

Status: draft, 2026-10-26. The work cut as it would be for a team of three (platform, backend,
web), with the order and the dependencies. Each package is one to three tickets' worth.

## Platform (P)

| Id | Package | Depends on | Done when |
|---|---|---|---|
| P1 | Terraform: Hetzner ARM server, firewall, volume, cloud-init installs k3s | | `kubectl get nodes` from the laptop |
| P2 | Cluster add-ons: ingress-nginx, cert-manager with Let's Encrypt issuer | P1 | A hello page on HTTPS at the domain |
| P3 | CloudNativePG operator and a one instance cluster, nightly backup to Object Storage | P1 | `psql` connects; a backup object exists |
| P4 | Redis | P1 | `redis-cli ping` from a pod |
| P5 | Helm chart: api, worker, beat, web, migrate job, secrets, probes, resources | B1, W1 | `helm install` on kind and on k3s |
| P6 | CI/CD: lint, test, buildx arm64 + amd64, push to ghcr, helm upgrade on main | P5 | A commit on main is live in minutes |
| P7 | Observability: structured logs, OpenTelemetry, metrics; optional Prometheus + Grafana | P5 | Operations page shows live numbers |

## Backend (B)

| Id | Package | Depends on | Done when |
|---|---|---|---|
| B1 | Django project skeleton, settings by env, DRF, OpenAPI, RFC 7807, health, Dockerfile | | `docker compose up` serves `/api/docs` |
| B2 | Weather adapter: client, timeouts, retries, cache, stale fallback, aggregation to days | B1 | W1, W2 pass with a mocked upstream and a live key |
| B3 | Locations: model, seed, CRUD, admin | B1 | Capitals listed; admin edits work |
| B4 | Brackets: configurable edges, grouping endpoint, Celery refresh task and schedule | B2, B3 | Brackets endpoint answers from cache; refresh visible |
| B5 | Catalogue: destination, package, departure models, CRUD, admin, seed | B3 | Three packages with departures visible |
| B6 | Bookable query: date range, danger derivation, remaining seats, pagination, indexes | B5 | Endpoint and tests; EXPLAIN documented |
| B7 | Booking: customer, booking, row lock, idempotency, cancel, concurrency test | B5 | Two parallel bookings, one 409 |
| B8 | Extras: suitability by customer risk appetite, weather aware filter, price and type filters | B4, B6, B7 | Documented and tested |
| B9 | Cross cutting: token auth and groups, audit log, soft delete | B5 | Writes recorded; deleted rows hidden |

## Web (W)

| Id | Package | Depends on | Done when |
|---|---|---|---|
| W1 | Next.js skeleton, shadcn, layout with the seven sections, Dockerfile | | Served at `/` |
| W2 | Overview and Decisions: render docs and ADRs, Mermaid diagrams | W1 | Docs readable on the site |
| W3 | Live demo: map of locations with brackets, forecast on click, bookable search, booking | B4, B6, B7 | A visitor can do the full loop |
| W4 | API page (Swagger embed), Plan page (this file), Roadmap | W1 | |
| W5 | Operations page from `/ops/status` and metrics | P7 | |
| W6 | Walkthrough: full screen, keyboard driven sections | W2, W3 | |

## Order

P1, B1, W1 in parallel. Then P2 to P4 with B2, B3. Then B4, B5, P5. Then B6, B7, P6, W2,
W3. Then B8, B9, P7, W4 to W6. The system is deployable after P6 with B1 to B5; everything
after that is additive.
