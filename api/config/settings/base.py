"""Settings shared by every environment.

Values that differ per environment come from environment variables (django-environ), never
from code: see .env.example at the repository root and docs/06-operations.md §8.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # the api/ folder

env = environ.Env()
# A local .env file is read when present (docker compose, laptop); production injects real
# environment variables and has no such file.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "core",
    "locations",
    "weather",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # admin and Swagger assets from the process
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL only (ADR 0007); DATABASE_URL like postgres://user:pass@host:5432/dbname.
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DJANGO_CONN_MAX_AGE", default=60)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Everything is stored in UTC; local days are computed per location (ADR 0013).
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user with role and partner (00-domain §5); must precede the first migration.
AUTH_USER_MODEL = "core.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # RFC 7807 problem details for every non-2xx response (core/errors.py).
    "EXCEPTION_HANDLER": "core.errors.problem_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Travel Agency API",
    "DESCRIPTION": "Weather, locations by temperature bracket, tour packages with dated "
    "departures and bookings.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Weather upstream (F1 to F3, ADR 0005). An empty key selects the fixture-backed mock client.
OPENWEATHER_API_KEY = env("OPENWEATHER_API_KEY", default="")
OPENWEATHER_BASE_URL = env("OPENWEATHER_BASE_URL", default="https://api.openweathermap.org")
OPENWEATHER_TIMEOUT_S = env.float("OPENWEATHER_TIMEOUT_S", default=5.0)
UPSTREAM_RETRIES = env.int("UPSTREAM_RETRIES", default=2)
# Budget shares per minute (sum under 80 % of the free tier's 60) and the breaker (06 §8).
UPSTREAM_REFRESH_SHARE = env.int("UPSTREAM_REFRESH_SHARE", default=40)
UPSTREAM_ADHOC_SHARE = env.int("UPSTREAM_ADHOC_SHARE", default=8)
UPSTREAM_MONTHLY_LIMIT = env.int("UPSTREAM_MONTHLY_LIMIT", default=1_000_000)
BREAKER_FAILURES = env.int("BREAKER_FAILURES", default=5)
BREAKER_COOLDOWN_S = env.int("BREAKER_COOLDOWN_S", default=60)

# Redis: ad hoc weather cache, budget and breaker state, Celery broker (ADR 0005).
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

# Celery (02 §8.4): idempotent tasks, late acks, hard time limits, schedule in code.
REFRESH_INTERVAL_S = env.int("REFRESH_INTERVAL_S", default=900)
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = None
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 20 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 18 * 60
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "weather-refresh-all": {
        "task": "weather.tasks.refresh_all",
        "schedule": REFRESH_INTERVAL_S,
        "kwargs": {"trigger": "scheduled"},
    },
    "weather-prune-samples": {
        "task": "weather.tasks.prune_samples",
        "schedule": 24 * 3600,  # daily; beat starts the clock when it starts
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
    # HTTP client libraries log full request URLs at INFO, query string included: never below
    # WARNING, or the upstream API key would land in the logs (N6.3).
    "loggers": {
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
    },
}
