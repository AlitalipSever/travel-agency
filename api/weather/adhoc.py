"""Current weather for any coordinate (W1): known locations from stored samples, others through
the ad hoc cache and the gateway with stale fallback (ADR 0005).

The result is a plain dict shaped like the API response so that the view only serialises it.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from django.conf import settings

from core.errors import RateLimited, UpstreamUnavailable
from core.redis_client import redis_connection
from locations.models import Location

from . import samples
from .domain.conditions import label_for
from .domain.geo import Point, cache_key, nearest_within, offset_label
from .upstream import breaker, gateway
from .upstream.client import UpstreamError
from .upstream.types import Observation

log = logging.getLogger(__name__)

FRESH_S = 600  # a cached value younger than this is served as "cached"
KEEP_S = 24 * 3600  # kept this long so an outage can still answer "stale"
LOCATIONS_CACHE_KEY = "locations:active"
LOCATIONS_CACHE_S = 60


@dataclass(frozen=True, slots=True)
class Current:
    lat: float
    lon: float
    timezone: str
    temp: float
    condition_code: int
    humidity: int | None
    wind_speed: float | None
    observed_at: datetime
    source: str  # live | cached | stale | sample
    age_s: int
    location_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "timezone": self.timezone,
            "temp": self.temp,
            "condition": label_for(self.condition_code),
            "condition_code": self.condition_code,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "observed_at": self.observed_at.isoformat().replace("+00:00", "Z"),
            "source": self.source,
            "age_s": self.age_s,
            "location_id": self.location_id,
        }


def _active_locations() -> list[tuple[Location, Point]]:
    """Active locations with their points; the id list is cached in Redis for a minute."""
    r = redis_connection()
    cached = r.get(LOCATIONS_CACHE_KEY)
    if cached:
        ids = json.loads(cached)
        rows = Location.objects.filter(pk__in=ids)
    else:
        rows = Location.objects.filter(active=True, deleted_at__isnull=True)
        r.set(LOCATIONS_CACHE_KEY, json.dumps([str(x.pk) for x in rows]), ex=LOCATIONS_CACHE_S)
    return [(loc, Point(float(loc.latitude), float(loc.longitude))) for loc in rows]


def known_location(lat: float, lon: float) -> Location | None:
    return nearest_within(Point(lat, lon), _active_locations())


def _from_sample(location: Location, lat: float, lon: float) -> Current | None:
    sample = samples.latest_observation(location)
    if sample is None:
        return None
    now = datetime.now(tz=UTC)
    return Current(
        lat=lat,
        lon=lon,
        timezone=location.timezone,
        temp=float(sample.temp),
        condition_code=sample.condition_code,
        humidity=None,
        wind_speed=None,
        observed_at=sample.slot_time,
        source="sample",
        age_s=int((now - sample.slot_time).total_seconds()),
        location_id=str(location.pk),
    )


def _serialise(obs: Observation) -> str:
    return json.dumps(
        {
            "temp": obs.temp,
            "condition_code": obs.condition_code,
            "humidity": obs.humidity,
            "wind_speed": obs.wind_speed,
            "observed_at": obs.observed_at.isoformat(),
            "timezone_offset_s": obs.timezone_offset_s,
            "stored_at": datetime.now(tz=UTC).isoformat(),
        }
    )


def _from_cache(raw: str, lat: float, lon: float, source: str) -> Current:
    data = json.loads(raw)
    stored_at = datetime.fromisoformat(data["stored_at"])
    return Current(
        lat=lat,
        lon=lon,
        timezone=offset_label(int(data["timezone_offset_s"])),
        temp=float(data["temp"]),
        condition_code=int(data["condition_code"]),
        humidity=data.get("humidity"),
        wind_speed=data.get("wind_speed"),
        observed_at=datetime.fromisoformat(data["observed_at"]),
        source=source,
        age_s=int((datetime.now(tz=UTC) - stored_at).total_seconds()),
    )


def get_current(lat: float, lon: float) -> Current:
    """W1: known location -> samples; otherwise cache, live, stale, or 503."""
    location = known_location(lat, lon)
    if location is not None:
        hit = _from_sample(location, lat, lon)
        if hit is not None:
            return hit  # a known location without samples yet falls through to the ad hoc path

    r = redis_connection()
    key = f"owm:current:{cache_key(lat, lon)}"
    raw = cast("str | None", r.get(key))  # decode_responses=True on the connection
    if raw:
        cached = _from_cache(raw, lat, lon, "cached")
        if cached.age_s <= FRESH_S:
            return cached

    try:
        obs = gateway.fetch_current(lat, lon, "adhoc")
    except gateway.BudgetExhausted as exc:
        if raw:
            return _from_cache(raw, lat, lon, "stale")
        raise RateLimited(
            "The weather upstream budget for ad hoc requests is spent for this minute.",
            headers={"Retry-After": "60"},
        ) from exc
    except (breaker.BreakerOpen, UpstreamError) as exc:
        if raw:
            return _from_cache(raw, lat, lon, "stale")
        log.warning("no stored value for %s,%s and upstream unavailable: %s", lat, lon, exc)
        raise UpstreamUnavailable(
            "Weather is not available for this coordinate right now.",
            headers={"Retry-After": str(int(settings.BREAKER_COOLDOWN_S))},
        ) from exc

    r.set(key, _serialise(obs), ex=KEEP_S)
    return Current(
        lat=lat,
        lon=lon,
        timezone=offset_label(obs.timezone_offset_s),
        temp=obs.temp,
        condition_code=obs.condition_code,
        humidity=obs.humidity,
        wind_speed=obs.wind_speed,
        observed_at=obs.observed_at,
        source="live",
        age_s=0,
    )
