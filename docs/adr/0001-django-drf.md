# 0001 Django and Django REST Framework as the application framework

Status: proposed
Date: 2026-10-26

## Context

The brief asks for an architecture aligned with a Python, Django, PostgreSQL and Redis stack.
The system needs a REST API, an admin interface for a manageable location list, an ORM with
migrations, and background jobs.

## Options

1. Django + DRF: batteries included, admin for free, mature ORM and migrations, Celery
   integration is standard. Heavier than needed for a tiny API.
2. FastAPI + SQLAlchemy: lighter, async first, excellent OpenAPI. No admin, migrations and
   auth assembled by hand, less aligned with the stated stack.
3. Flask: minimal, everything assembled by hand.

## Decision

Django + DRF. The admin covers the "manageable list" requirement with no custom code, the ORM
and migrations carry the catalogue model, and the stack matches the brief. The weight is
accepted; the API surface is small enough that DRF's generic views and serializers stay thin.

## Consequences

Thin views, logic in per app `services` modules so that the framework does not leak into the
domain. drf-spectacular for the schema. Celery with Redis as broker for background work. Async
is not needed for the request path because the upstream calls are moved to the worker (0005).
