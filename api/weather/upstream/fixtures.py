"""Recorded upstream payloads for tests and for running without an API key (L1 mock mode).

Files live in api/fixtures/openweather/<kind>_<slug>.json with the raw OpenWeatherMap JSON.
The mock picks the recorded coordinate nearest to the request and shifts timestamps so that
the data always looks fresh: the forecast starts at the next full three hour slot from now.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings

from .client import parse_current, parse_forecast
from .types import Forecast, Observation

FIXTURE_DIR = Path(settings.BASE_DIR) / "fixtures" / "openweather"


@lru_cache(maxsize=1)
def _recorded() -> list[tuple[str, float, float]]:
    """(slug, lat, lon) for every recorded place, from the current_<slug>.json files."""
    places = []
    for path in sorted(FIXTURE_DIR.glob("current_*.json")):
        data = json.loads(path.read_text())
        coord = data.get("coord") or {}
        places.append(
            (path.stem.removeprefix("current_"), float(coord["lat"]), float(coord["lon"]))
        )
    if not places:
        raise RuntimeError(f"no recorded fixtures in {FIXTURE_DIR}")
    return places


def nearest_slug(lat: float, lon: float) -> str:
    return min(_recorded(), key=lambda p: math.hypot(p[1] - lat, p[2] - lon))[0]


def load(kind: str, slug: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / f"{kind}_{slug}.json").read_text())


def _shift_current(data: dict[str, Any]) -> dict[str, Any]:
    now = int(datetime.now(tz=UTC).timestamp())
    delta = now - int(data["dt"])
    out = json.loads(json.dumps(data))
    out["dt"] = now
    for key in ("sunrise", "sunset"):
        if key in out.get("sys", {}):
            out["sys"][key] = int(out["sys"][key]) + delta
    return out


def _shift_forecast(data: dict[str, Any]) -> dict[str, Any]:
    """Move the recorded slots so the first one is the next full three hour slot from now."""
    out = json.loads(json.dumps(data))
    items = out.get("list") or []
    if not items:
        return out
    now = datetime.now(tz=UTC)
    next_slot = (now + timedelta(hours=3)).replace(minute=0, second=0, microsecond=0)
    next_slot -= timedelta(hours=next_slot.hour % 3)
    delta = int(next_slot.timestamp()) - int(items[0]["dt"])
    for item in items:
        item["dt"] = int(item["dt"]) + delta
        item["dt_txt"] = datetime.fromtimestamp(item["dt"], tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
    for key in ("sunrise", "sunset"):
        if key in out.get("city", {}):
            out["city"][key] = int(out["city"][key]) + delta
    return out


class MockWeatherClient:
    def fetch_current(self, lat: float, lon: float) -> Observation:
        return parse_current(_shift_current(load("current", nearest_slug(lat, lon))), lat, lon)

    def fetch_forecast(self, lat: float, lon: float) -> Forecast:
        return parse_forecast(_shift_forecast(load("forecast", nearest_slug(lat, lon))), lat, lon)
