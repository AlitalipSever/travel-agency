"""Background work for weather (W4.2, W4.4, ADR 0005, 0012): scheduled refresh of every known
location, spread over the interval and inside the refresh share; retention.

Tasks are idempotent (upserts), so a retry after a crash is safe (acks_late in settings).
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from celery import shared_task
from django.conf import settings

from core import redis_client, settings_store
from locations.models import Location

from . import samples
from .models import RefreshTrigger
from .upstream import breaker, budget, gateway
from .upstream.client import UpstreamError

log = logging.getLogger(__name__)

LOCK_KEY = "owm:refresh:lock"
CALLS_PER_LOCATION = 2  # current + forecast


def spacing_seconds(n_locations: int) -> float:
    """Seconds between two locations so the run spreads over the interval and never exceeds
    the refresh share per minute; the larger of the two bounds wins (W4.2)."""
    if n_locations <= 0:
        return 0.0
    interval = float(settings.REFRESH_INTERVAL_S)
    by_interval = interval / n_locations
    by_share = 60.0 / max(budget.share_limit("refresh") / CALLS_PER_LOCATION, 1)
    return max(by_interval, by_share)


def _sleep(seconds: float) -> None:  # separated so tests can neutralise it
    if seconds > 0:
        time.sleep(seconds)


def refresh_location_sync(location: Location) -> int:
    """Fetch current and forecast for one location through the gateway and store them.

    Returns the number of upstream calls used. Waits for the next minute when the refresh
    share is spent; raises UpstreamError (after the gateway's retries) or BreakerOpen.
    """
    calls = 0
    for _attempt in range(3):
        try:
            obs = gateway.fetch_current(
                float(location.latitude), float(location.longitude), "refresh"
            )
            calls += 1
            fc = gateway.fetch_forecast(
                float(location.latitude), float(location.longitude), "refresh"
            )
            calls += 1
            samples.store_observation(location, obs)
            samples.store_forecast(location, fc)
            return calls
        except gateway.BudgetExhausted:
            wait = 60 - datetime.now(tz=UTC).second + 1
            log.info("refresh share spent, waiting %ss (%s)", wait, location)
            _sleep(wait)
    raise UpstreamError("refresh share stayed exhausted for three minutes")


@shared_task(name="weather.tasks.refresh_all")
def refresh_all(trigger: str = RefreshTrigger.SCHEDULED) -> dict[str, int]:
    """One run over every active location; skipped when a previous run still holds the lock."""
    r = redis_client.redis_connection()
    if not r.set(LOCK_KEY, "1", nx=True, ex=int(settings.CELERY_TASK_TIME_LIMIT)):
        log.warning("refresh_all skipped: a run is still in progress")
        return {"skipped": 1}
    started = time.monotonic()
    try:
        locations = list(Location.objects.filter(active=True, deleted_at__isnull=True))
        run = samples.start_run(RefreshTrigger(trigger), locations=len(locations))
        pause = spacing_seconds(len(locations))
        calls = failures = 0
        notes: list[str] = []
        for index, location in enumerate(locations):
            try:
                calls += refresh_location_sync(location)
            except breaker.BreakerOpen:
                failures += 1
                notes.append(f"{location}: breaker open")
                log.warning("breaker open, skipping %s", location)
            except UpstreamError as exc:
                failures += 1
                notes.append(f"{location}: {exc}")
                log.warning("refresh failed for %s: %s", location, exc)
            if index < len(locations) - 1:
                _sleep(pause)
        elapsed = int(time.monotonic() - started)
        samples.finish_run(
            run,
            calls_used=calls,
            failures=failures,
            effective_interval_s=max(elapsed, int(settings.REFRESH_INTERVAL_S)),
            notes="; ".join(notes)[:2000],
        )
        return {"locations": len(locations), "calls": calls, "failures": failures}
    finally:
        r.delete(LOCK_KEY)


@shared_task(name="weather.tasks.refresh_one_now")
def refresh_one_now(location_id: str) -> dict[str, int]:
    """Immediate refresh of one location (L1.5, on create); does not take the run lock."""
    location = Location.objects.get(pk=location_id)
    run = samples.start_run(RefreshTrigger.ON_CREATE, locations=1)
    try:
        calls = refresh_location_sync(location)
        samples.finish_run(run, calls_used=calls, failures=0)
        return {"calls": calls}
    except (UpstreamError, breaker.BreakerOpen) as exc:
        samples.finish_run(run, calls_used=0, failures=1, notes=str(exc))
        return {"calls": 0, "failures": 1}


@shared_task(name="weather.tasks.prune_samples")
def prune_samples() -> int:
    return samples.prune(settings_store.sample_retention_days())
