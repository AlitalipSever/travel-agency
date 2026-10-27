# syntax=docker/dockerfile:1.7
# One image, four commands: gunicorn (api), celery worker, celery beat, manage.py migrate.
# Multi-stage: dependencies are installed with uv from the lock file in a builder stage; the
# runtime stage carries only the virtual environment, the code and the collected static files.

ARG PYTHON_VERSION=3.13

# ---------- builder ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so a code change does not reinstall them (layer cache).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Admin and Swagger assets; a throwaway secret, no database needed for collectstatic.
RUN DJANGO_SECRET_KEY=build DATABASE_URL=postgres://x:x@x/x DJANGO_SETTINGS_MODULE=config.settings.production \
    /app/.venv/bin/python manage.py collectstatic --noinput

# ---------- runtime ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

# tzdata is updated on every build: daylight saving rules change (F4, 06 §12).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home /app app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

USER app
EXPOSE 8000

# api by default; worker, beat and migrate override the command (chart/, docker-compose.yml).
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "30", "--access-logfile", "-"]
