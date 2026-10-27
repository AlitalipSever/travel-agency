"""Service over WeatherSample and RefreshRun: store what the gateway fetched, read it back.

Writes are upserts in one statement per fetch (newest wins per location, slot and kind). The
"observation beats forecast for the same hour" rule is applied on read by the summary code,
so writing stays simple and the rule lives in one place (ADR 0012, 0013).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.db.models import QuerySet

from locations.models import Location

from .models import RefreshRun, RefreshTrigger, SampleKind, WeatherSample
from .upstream.types import Forecast, Observation

_UPDATE_FIELDS = [
    "fetched_at",
    "temp",
    "temp_min",
    "temp_max",
    "condition_code",
    "pop",
    "is_day",
    "raw",
]


def _dec(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def _dec_opt(value: float | None) -> Decimal | None:
    return None if value is None else _dec(value)


def store_forecast(location: Location, forecast: Forecast, keep_raw: bool = False) -> int:
    rows = [
        WeatherSample(
            location=location,
            slot_time=slot.slot_time,
            kind=SampleKind.FORECAST,
            fetched_at=forecast.fetched_at,
            temp=_dec(slot.temp),
            temp_min=_dec(slot.temp_min),
            temp_max=_dec(slot.temp_max),
            condition_code=slot.condition_code,
            pop=_dec_opt(slot.pop),
            is_day=slot.is_day,
            raw=None,
        )
        for slot in forecast.slots
    ]
    WeatherSample.objects.bulk_create(
        rows,
        update_conflicts=True,
        unique_fields=["location", "slot_time", "kind"],
        update_fields=_UPDATE_FIELDS,
    )
    return len(rows)


def store_observation(location: Location, observation: Observation) -> WeatherSample:
    sample, _ = WeatherSample.objects.update_or_create(
        location=location,
        slot_time=observation.observed_at,
        kind=SampleKind.OBSERVATION,
        defaults={
            "fetched_at": datetime.now(tz=UTC),
            "temp": _dec(observation.temp),
            "temp_min": _dec(observation.temp_min),
            "temp_max": _dec(observation.temp_max),
            "condition_code": observation.condition_code,
            "pop": None,
            "is_day": observation.is_day,
            "raw": None,
        },
    )
    return sample


def latest_observation(location: Location) -> WeatherSample | None:
    return (
        WeatherSample.objects.filter(location=location, kind=SampleKind.OBSERVATION)
        .order_by("-slot_time")
        .first()
    )


def samples_between(location: Location, start: datetime, end: datetime) -> QuerySet[WeatherSample]:
    """Samples with slot_time in [start, end), both kinds, oldest first."""
    return WeatherSample.objects.filter(
        location=location, slot_time__gte=start, slot_time__lt=end
    ).order_by("slot_time", "kind")


def prune(older_than_days: int, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=older_than_days)
    deleted, _ = WeatherSample.objects.filter(slot_time__lt=cutoff).delete()
    runs, _ = RefreshRun.objects.filter(started_at__lt=cutoff).delete()
    return deleted + runs


def start_run(trigger: RefreshTrigger, locations: int) -> RefreshRun:
    return RefreshRun.objects.create(
        started_at=datetime.now(tz=UTC), trigger=trigger, locations=locations
    )


def finish_run(
    run: RefreshRun,
    *,
    calls_used: int,
    failures: int,
    effective_interval_s: int | None = None,
    notes: str = "",
) -> RefreshRun:
    run.finished_at = datetime.now(tz=UTC)
    run.calls_used = calls_used
    run.failures = failures
    run.effective_interval_s = effective_interval_s
    run.notes = notes
    run.save(
        update_fields=["finished_at", "calls_used", "failures", "effective_interval_s", "notes"]
    )
    return run


def last_run() -> RefreshRun | None:
    return RefreshRun.objects.order_by("-started_at").first()
