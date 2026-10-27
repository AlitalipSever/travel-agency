# api

The Django project: the REST API (`/api/v1`), the admin, the Celery worker and beat, and the
migrate job all run from this one image with different commands.

Apps are bounded contexts (docs/02-architecture.md §5.2): `core` (auth and roles, errors,
history, health, settings), `weather`, `locations`, `catalog`, `booking`. Each app keeps its
models, services, views and `tests/` together.

## Run

Toolchain: Python 3.13 pinned in `.python-version`, dependencies managed by `uv`
(`pyproject.toml`, `uv.lock`).

```
uv sync          # create .venv and install locked dependencies
uv run pytest    # tests
uv run ruff check . && uv run mypy .
```

The full stack (PostgreSQL, Redis, worker, beat, site) runs from the repository root with
`make up` (docs/06-operations.md §1). Status: skeleton in progress (work package B1).
