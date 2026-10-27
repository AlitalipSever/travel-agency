"""Celery application: Redis broker, tasks discovered from every app's tasks.py.

Worker: celery -A config worker; scheduler: celery -A config beat (one instance only).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("travel_agency")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
