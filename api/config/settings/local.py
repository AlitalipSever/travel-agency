"""Laptop and docker compose: debug on, permissive hosts, a default database URL."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "local-only-not-a-secret")
os.environ.setdefault("DATABASE_URL", "postgres://travel:travel@localhost:5432/travel")

from .base import *  # noqa: E402, F403

DEBUG = env.bool("DJANGO_DEBUG", default=True)  # noqa: F405
ALLOWED_HOSTS = ["*"]

# The browsable API is handy on a laptop; production serves JSON only (see production.py).
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
