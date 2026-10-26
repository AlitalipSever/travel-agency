# Architecture decision records

MADR style, one file per decision, numbered, never edited after acceptance; a later ADR
supersedes an earlier one. Status: proposed, accepted, superseded, rejected.

| # | Decision | Status |
|---|---|---|
| [0001](0001-django-drf.md) | Django and Django REST Framework as the application framework | accepted |
| [0002](0002-departure-capacity.md) | Capacity belongs to a departure date, bookings take a row lock | accepted |
| [0003](0003-danger-score.md) | Danger score scale, "at most" semantics, derived in the query | accepted |
| [0004](0004-temperature-brackets.md) | Temperature brackets are configurable fixed edges, quantile mode optional | accepted |
| [0005](0005-weather-cache-and-refresh.md) | Known locations refreshed by a scheduled job into PostgreSQL; Redis for ad hoc coordinates; stale fallback | accepted |
| [0006](0006-k3s-on-hetzner.md) | Deploy on k3s on one Hetzner server with one Helm chart; cloud independence over managed services | accepted |
| [0007](0007-postgres-operator.md) | PostgreSQL through the CloudNativePG operator | accepted |
| [0008](0008-no-event-streaming-yet.md) | No event streaming (Kafka) in this iteration | accepted |
| [0009](0009-registry-and-ci.md) | Images in GitHub Container Registry, built by GitHub Actions for arm64 and amd64 | accepted |
| [0010](0010-docs-arc42-c4.md) | Architecture documentation in arc42 structure with C4 diagrams in Mermaid | accepted |
| [0011](0011-date-range-on-departure.md) | The date range filter applies to the departure date; packages carry a duration | accepted |
| [0012](0012-persist-weather-samples.md) | Forecast slots and observations are persisted for known locations | accepted |
| [0013](0013-daily-summary-and-time.md) | Daily summary rules (mean, min, max; daytime significant weather) and UTC storage with IANA local days | accepted |
| [0014](0014-history-by-triggers.md) | Change history by database triggers (per-table history, actor from session context), not an application audit log | accepted |
