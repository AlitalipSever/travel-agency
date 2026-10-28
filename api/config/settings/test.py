"""pytest: deterministic and fast; the database comes from DATABASE_URL (CI sets it)."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")
os.environ.setdefault("DATABASE_URL", "postgres://travel:travel@localhost:5432/travel")

from .base import *  # noqa: E402, F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

# Fast password hashing in tests only; never in production.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# No collected static files in tests.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Tests never call the real upstream; the mock client serves recorded fixtures.
OPENWEATHER_API_KEY = ""

# Tasks run inline in tests; no worker, no broker round trip.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# In-memory cache for throttles in tests (Redis itself is faked per test).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
