"""Operations status (N5.5, 04-api §8): what the weather pipeline is doing, in one document."""

from __future__ import annotations

from typing import Any

from django.conf import settings

from . import samples, stats
from .models import WeatherSample
from .upstream import breaker, budget


def _run(run: Any) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "run_id": str(run.pk),
        "trigger": run.trigger,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "locations": run.locations,
        "calls_used": run.calls_used,
        "failures": run.failures,
        "effective_interval_s": run.effective_interval_s,
        "notes": run.notes,
    }


def status() -> dict[str, Any]:
    return {
        "last_run": _run(samples.last_run()),
        "last_finished_run": _run(samples.last_finished_run()),
        "configured_interval_s": int(settings.REFRESH_INTERVAL_S),
        "upstream": budget.snapshot(),
        "breaker": breaker.snapshot(),
        "adhoc_cache": stats.adhoc_snapshot(),
        "samples": {
            "count": WeatherSample.objects.count(),
            "retention_days": settings_value("sample_retention_days"),
        },
        "versions": {
            "api": settings.SPECTACULAR_SETTINGS.get("VERSION"),
            "commit": settings.GIT_COMMIT,
            "chart": settings.CHART_VERSION,
        },
    }


def settings_value(key: str) -> Any:
    from core import settings_store

    try:
        return settings_store.get(key)
    except Exception:  # noqa: BLE001  the table may be empty in a fresh database
        return None
