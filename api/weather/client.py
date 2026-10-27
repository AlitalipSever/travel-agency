"""OpenWeatherMap client: the only module that knows the upstream's URLs and JSON (ADR 0005).

Two entry points, fetch_current and fetch_forecast, return our own types. Failures are mapped
to a small exception family that the budget and breaker logic (step 2) and the views act on.
Without an API key the mock client serves recorded payloads from api/fixtures/openweather.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx
from django.conf import settings

from .types import Forecast, ForecastSlot, Observation

log = logging.getLogger(__name__)


class UpstreamError(Exception):
    """The upstream could not be used: network error, timeout, 5xx, unparsable body."""


class UpstreamRateLimited(UpstreamError):
    """HTTP 429 from the upstream: our budget accounting was wrong or shared."""


class UpstreamRejected(UpstreamError):
    """HTTP 4xx other than 429: bad key or bad request; retrying will not help."""


class WeatherClient(Protocol):
    def fetch_current(self, lat: float, lon: float) -> Observation: ...

    def fetch_forecast(self, lat: float, lon: float) -> Forecast: ...


def parse_current(data: dict[str, Any], lat: float, lon: float) -> Observation:
    main = data["main"]
    weather = (data.get("weather") or [{}])[0]
    sys = data.get("sys") or {}
    observed_at = datetime.fromtimestamp(int(data["dt"]), tz=UTC)
    sunrise, sunset = sys.get("sunrise"), sys.get("sunset")
    is_day = bool(sunrise and sunset and sunrise <= data["dt"] < sunset)
    return Observation(
        lat=lat,
        lon=lon,
        observed_at=observed_at,
        temp=float(main["temp"]),
        temp_min=float(main.get("temp_min", main["temp"])),
        temp_max=float(main.get("temp_max", main["temp"])),
        humidity=int(main["humidity"]) if "humidity" in main else None,
        wind_speed=float(data["wind"]["speed"]) if data.get("wind") else None,
        condition_code=int(weather.get("id", 0)),
        is_day=is_day,
        timezone_offset_s=int(data.get("timezone", 0)),
    )


def parse_forecast(data: dict[str, Any], lat: float, lon: float) -> Forecast:
    city = data.get("city") or {}
    slots = []
    for item in data.get("list") or []:
        main = item["main"]
        weather = (item.get("weather") or [{}])[0]
        slots.append(
            ForecastSlot(
                slot_time=datetime.fromtimestamp(int(item["dt"]), tz=UTC),
                temp=float(main["temp"]),
                temp_min=float(main.get("temp_min", main["temp"])),
                temp_max=float(main.get("temp_max", main["temp"])),
                condition_code=int(weather.get("id", 0)),
                pop=float(item["pop"]) if item.get("pop") is not None else None,
                is_day=(item.get("sys") or {}).get("pod", "d") == "d",
            )
        )
    return Forecast(
        lat=lat,
        lon=lon,
        fetched_at=datetime.now(tz=UTC),
        timezone_offset_s=int(city.get("timezone", 0)),
        slots=tuple(slots),
    )


class HttpWeatherClient:
    """Real client: explicit timeouts, no retries here (the caller decides, step 2)."""

    def __init__(self, api_key: str, base_url: str, timeout_s: float) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_s, connect=min(timeout_s, 3.0)),
            headers={"User-Agent": "travel-agency/0.1"},
        )
        self._params = {"appid": api_key, "units": "metric"}

    def _get(self, path: str, lat: float, lon: float) -> dict[str, Any]:
        try:
            response = self._client.get(path, params={**self._params, "lat": lat, "lon": lon})
        except httpx.TimeoutException as exc:
            raise UpstreamError(f"timeout calling {path}") from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(f"network error calling {path}: {exc.__class__.__name__}") from exc
        if response.status_code == 429:
            raise UpstreamRateLimited("upstream answered 429")
        if 400 <= response.status_code < 500:
            raise UpstreamRejected(f"upstream answered {response.status_code} for {path}")
        if response.status_code >= 500:
            raise UpstreamError(f"upstream answered {response.status_code} for {path}")
        try:
            data = response.json()
        except ValueError as exc:
            raise UpstreamError("upstream body is not JSON") from exc
        if not isinstance(data, dict):
            raise UpstreamError("upstream body is not an object")
        return data

    def fetch_current(self, lat: float, lon: float) -> Observation:
        return parse_current(self._get("/data/2.5/weather", lat, lon), lat, lon)

    def fetch_forecast(self, lat: float, lon: float) -> Forecast:
        return parse_forecast(self._get("/data/2.5/forecast", lat, lon), lat, lon)


def get_client() -> WeatherClient:
    """The configured client: real when an API key is set, otherwise the fixture mock."""
    key = getattr(settings, "OPENWEATHER_API_KEY", "")
    if not key:
        from .fixtures import MockWeatherClient

        return MockWeatherClient()
    return HttpWeatherClient(
        api_key=key,
        base_url=settings.OPENWEATHER_BASE_URL,
        timeout_s=settings.OPENWEATHER_TIMEOUT_S,
    )
