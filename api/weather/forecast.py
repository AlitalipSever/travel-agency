"""Five day forecast for a coordinate (W2): known locations from stored samples, ad hoc
coordinates through the cache and the gateway; daily summaries by the rules of domain/summary.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast
from zoneinfo import ZoneInfo

from django.conf import settings

from core.errors import RateLimited, UpstreamUnavailable
from core.redis_client import redis_connection
from locations.models import Location

from . import samples, stats
from .adhoc import KEEP_S, known_location
from .domain.geo import cache_key, offset_label
from .domain.summary import DaySummary, summarize
from .upstream import breaker, gateway
from .upstream.client import UpstreamError
from .upstream.types import Forecast

log = logging.getLogger(__name__)

FRESH_S = 600


@dataclass(frozen=True, slots=True)
class SlotRow:
    """A forecast slot in the shape the summary rules read (SampleLike)."""

    slot_time: datetime
    kind: str
    temp: float
    temp_min: float
    temp_max: float
    condition_code: int
    is_day: bool | None


def _day_dict(d: DaySummary) -> dict[str, Any]:
    out = asdict(d)
    out["date"] = d.date.isoformat()
    for key in ("temp_avg", "temp_min", "temp_max"):
        if out[key] != out[key]:  # NaN: a day with no data at all
            out[key] = None
    return out


def _response(
    lat: float,
    lon: float,
    tz_label: str,
    as_of: datetime,
    source: str,
    today: DaySummary | None,
    days: list[DaySummary],
    location_id: str | None,
) -> dict[str, Any]:
    return {
        "lat": lat,
        "lon": lon,
        "timezone": tz_label,
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "source": source,
        "today": None if today is None else _day_dict(today),
        "days": [_day_dict(d) for d in days],
        "location_id": location_id,
    }


def _from_samples(location: Location, lat: float, lon: float) -> dict[str, Any] | None:
    zone = ZoneInfo(location.timezone)
    now = datetime.now(tz=UTC)
    today = now.astimezone(zone).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=zone).astimezone(UTC)
    end = start + timedelta(days=7)
    rows = list(samples.samples_between(location, start, end))
    if not any(r.slot_time > now for r in rows):
        return None  # no forecast stored yet (new location): use the ad hoc path
    today_s, days = summarize(rows, zone, today=today)
    as_of = max(r.fetched_at for r in rows)
    return _response(lat, lon, location.timezone, as_of, "sample", today_s, days, str(location.pk))


def _rows_from_forecast(fc: Forecast) -> list[SlotRow]:
    return [
        SlotRow(s.slot_time, "forecast", s.temp, s.temp_min, s.temp_max, s.condition_code, s.is_day)
        for s in fc.slots
    ]


def _serialise(fc: Forecast) -> str:
    return json.dumps(
        {
            "fetched_at": fc.fetched_at.isoformat(),
            "timezone_offset_s": fc.timezone_offset_s,
            "stored_at": datetime.now(tz=UTC).isoformat(),
            "slots": [
                [
                    s.slot_time.isoformat(),
                    s.temp,
                    s.temp_min,
                    s.temp_max,
                    s.condition_code,
                    s.is_day,
                ]
                for s in fc.slots
            ],
        }
    )


def _from_cache(raw: str, lat: float, lon: float, source: str) -> dict[str, Any]:
    data = json.loads(raw)
    offset = int(data["timezone_offset_s"])
    zone = timezone(timedelta(seconds=offset))
    rows = [
        SlotRow(
            datetime.fromisoformat(t),
            "forecast",
            float(a),
            float(b),
            float(c),
            int(code),
            bool(day),
        )
        for t, a, b, c, code, day in data["slots"]
    ]
    today = datetime.now(tz=UTC).astimezone(zone).date()
    today_s, days = summarize(rows, zone, today=today)
    return _response(
        lat,
        lon,
        offset_label(offset),
        datetime.fromisoformat(data["fetched_at"]),
        source,
        today_s,
        days,
        None,
    )


def get_forecast(lat: float, lon: float) -> dict[str, Any]:
    """W2: known location -> samples; otherwise cache, live, stale, or 503 / 429."""
    location = known_location(lat, lon)
    if location is not None:
        hit = _from_samples(location, lat, lon)
        if hit is not None:
            return hit

    r = redis_connection()
    key = f"owm:forecast:{cache_key(lat, lon)}"
    raw = cast("str | None", r.get(key))
    if raw:
        stored_at = datetime.fromisoformat(json.loads(raw)["stored_at"])
        if (datetime.now(tz=UTC) - stored_at).total_seconds() <= FRESH_S:
            stats.record_adhoc("hit")
            return _from_cache(raw, lat, lon, "cached")

    try:
        fc = gateway.fetch_forecast(lat, lon, "adhoc")
    except gateway.BudgetExhausted as exc:
        if raw:
            stats.record_adhoc("hit")
            return _from_cache(raw, lat, lon, "stale")
        raise RateLimited(
            "The weather upstream budget for ad hoc requests is spent for this minute.",
            headers={"Retry-After": "60"},
        ) from exc
    except (breaker.BreakerOpen, UpstreamError) as exc:
        if raw:
            stats.record_adhoc("hit")
            return _from_cache(raw, lat, lon, "stale")
        log.warning("no stored forecast for %s,%s and upstream unavailable: %s", lat, lon, exc)
        raise UpstreamUnavailable(
            "Forecast is not available for this coordinate right now.",
            headers={"Retry-After": str(int(settings.BREAKER_COOLDOWN_S))},
        ) from exc

    r.set(key, _serialise(fc), ex=KEEP_S)
    stats.record_adhoc("miss")
    zone = timezone(timedelta(seconds=fc.timezone_offset_s))
    today = datetime.now(tz=UTC).astimezone(zone).date()
    today_s, days = summarize(_rows_from_forecast(fc), zone, today=today)
    return _response(
        lat, lon, offset_label(fc.timezone_offset_s), fc.fetched_at, "live", today_s, days, None
    )
