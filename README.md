# travel-agency

Backend for a travel agency: live weather for the agency's locations, tour packages with
dated departures and capacity, and a bookable-packages search by date range and danger score.
Built as a production-shaped system: Django + DRF API, Celery workers, PostgreSQL, Redis, a
Next.js case study site, packaged as a Helm chart and running on k3s.

## Layout

One repository (monorepo) for the backend, the site, the chart and the infrastructure, so that
one commit can change the API and its deployment together and CI runs from one place.

```
Makefile              Single entry point: make up, test, seed, demo, kind-up, deploy
docker-compose.yml    Local development stack: api, worker, beat, web, postgres, redis
.env.example          Names of the environment variables, never values
docs/                 Domain, requirements, architecture (arc42), data model, API, ADRs, plans
api/                  Django project, one image: config/ (settings, urls, celery) and the apps
                      core/, weather/, locations/, catalog/, booking/, each with its tests/;
                      fixtures/ holds recorded upstream payloads for tests and mock mode
web/                  Next.js case study site, one image: app/ (pages), components/, lib/
chart/                Helm chart: templates/ and values-local, values-hetzner, values-azure
infra/                Terraform for the Hetzner server, firewall, volume and k3s bootstrap
kind/                 kind cluster config and local MinIO for the production rehearsal
.github/workflows/    CI: lint, test, build, push, deploy
```

Each top level folder carries its own README with what is inside and how to run it. The
folders appear as their work packages land (docs/05-work-packages.md).

## Documents

Start at [docs/README.md](docs/README.md).

## Status

Documents reviewed; build in progress on feature branches (develop integrates, main deploys).
