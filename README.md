# travel-agency

Backend for a travel agency: live weather for the agency's locations, tour packages with
dated departures and capacity, and a bookable-packages search by date range and danger score.
Built as a production-shaped system: Django + DRF API, Celery workers, PostgreSQL, Redis, a
Next.js case study site, packaged as a Helm chart and running on k3s.

## Layout

```
docs/        Requirements, architecture (arc42 + C4), ADRs, work packages, runbook
api/         Django project (DRF, Celery)                      [to come]
web/         Next.js case study site                           [to come]
chart/       Helm chart, one template set, several values files [to come]
infra/       Terraform: Hetzner server, firewall, volume, k3s   [to come]
.github/     CI: lint, test, build, push to ghcr, deploy       [to come]
```

## Documents

Start at [docs/README.md](docs/README.md).

## Status

Documentation phase. Nothing runs yet.
