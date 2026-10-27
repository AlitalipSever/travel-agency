"""Our own shapes for upstream weather data (02 §8.4: one adapter, upstream JSON stays inside).

Everything downstream (samples, summaries, brackets, the API) sees these classes, never the
OpenWeatherMap payload. Times are UTC-aware datetimes; temperatures are degrees Celsius (A14).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Observation:
    """Current weather at a coordinate (W1)."""

    lat: float
    lon: float
    observed_at: datetime
    temp: float
    temp_min: float
    temp_max: float
    humidity: int | None
    wind_speed: float | None
    condition_code: int
    is_day: bool
    timezone_offset_s: int  # the upstream's offset for the place, used for ad hoc coordinates


@dataclass(frozen=True, slots=True)
class ForecastSlot:
    """One three hour slot of the five day forecast (F1)."""

    slot_time: datetime  # UTC, start of the slot
    temp: float
    temp_min: float
    temp_max: float
    condition_code: int
    pop: float | None  # probability of precipitation 0..1
    is_day: bool


@dataclass(frozen=True, slots=True)
class Forecast:
    lat: float
    lon: float
    fetched_at: datetime
    timezone_offset_s: int
    slots: tuple[ForecastSlot, ...]
