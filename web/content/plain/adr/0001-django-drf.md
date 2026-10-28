# 0001 Django and Django REST Framework as the application framework

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: A9; L1; N1

## Context

The brief asks for an architecture aligned with a Python, Django, PostgreSQL and Redis stack.

The system needs:

- a REST API;
- an admin interface for a manageable location list;
- an ORM with migrations;
- background jobs.

## Options

1. Django + DRF: batteries included, and the admin comes for free. The ORM and migrations are
   mature, and Celery integration is standard. It is heavier than needed for a tiny API.
2. FastAPI + SQLAlchemy: lighter, async first, with excellent OpenAPI. There is no admin, and
   migrations and auth are assembled by hand. It is less aligned with the stated stack.
3. Flask: minimal, everything assembled by hand.

## Decision

Django + DRF.

- The admin covers the "manageable list" requirement with no custom code.
- The ORM and migrations carry the catalogue model.
- The stack matches the brief.

The weight is accepted. The API surface is small enough that DRF's generic views and
serializers stay thin.

## Consequences

Views stay thin. Logic lives in per app `services` modules, so the framework does not leak
into the domain.

The Django admin is the operations UI for locations, destinations, packages and departures
(role `ops`). The API serves the same writes for automation.

Supporting choices:

- drf-spectacular for the schema.
- Celery with Redis as broker for background work.

Async is not needed for the request path, because the upstream calls are moved to the worker
(0005).
