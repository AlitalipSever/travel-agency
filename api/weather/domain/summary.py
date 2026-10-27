"""Daily summaries from three hour slots and observations (W2, W3, ADR 0013). Pure functions.

Input: samples of one location (any kind), each with slot_time (UTC, aware), temp, temp_min,
temp_max, condition_code, is_day, kind. Output: one DaySummary per local calendar day.

Rules: a slot belongs to the local day in which it starts; an observation beats a forecast for
the same hour; temperature is mean, min and max over the day's slots to one decimal; the label
comes from daytime slots with significant weather first (thunderstorm, rain, snow, fog), else
the more frequent of cloudy and clear, cloudy on a tie; with no daytime slot all slots count;
without an is_day mark, 06:00 to 18:00 local is daytime. partial marks a day with fewer slots
than its length allows (8 normally, 7 or 9 on a daylight saving transition).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from decimal import Decimal
from typing import Protocol

from .conditions import SIGNIFICANT, label_for

SLOT_HOURS = 3


class SampleLike(Protocol):
    """Read-only view of a sample; WeatherSample rows and test doubles both satisfy it."""

    @property
    def slot_time(self) -> datetime: ...
    @property
    def kind(self) -> str: ...
    @property
    def temp(self) -> Decimal | float: ...
    @property
    def temp_min(self) -> Decimal | float: ...
    @property
    def temp_max(self) -> Decimal | float: ...
    @property
    def condition_code(self) -> int: ...
    @property
    def is_day(self) -> bool | None: ...


@dataclass(frozen=True, slots=True)
class DaySummary:
    date: date
    temp_avg: float
    temp_min: float
    temp_max: float
    condition: str
    observed_samples: int
    forecast_samples: int
    partial: bool


def local_day(moment: datetime, zone: tzinfo) -> date:
    return moment.astimezone(zone).date()


def expected_slots(day: date, zone: tzinfo) -> int:
    """How many three hour slots the local day holds: 8, or 7 / 9 across a DST change.

    Upstream slots start at UTC hours divisible by three; count the starts inside the day.
    """
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    end = end.astimezone(UTC)
    first = start.replace(minute=0, second=0, microsecond=0)
    if first < start:
        first += timedelta(hours=1)
    while first.hour % SLOT_HOURS:
        first += timedelta(hours=1)
    count = 0
    t = first
    while t < end:
        count += 1
        t += timedelta(hours=SLOT_HOURS)
    return max(1, count)


def _is_day(sample: SampleLike, zone: tzinfo) -> bool:
    if sample.is_day is not None:
        return bool(sample.is_day)
    hour = sample.slot_time.astimezone(zone).hour
    return 6 <= hour < 18


def dedupe_observation_over_forecast(samples: Sequence[SampleLike]) -> list[SampleLike]:
    """One sample per hour; when both kinds exist for the same hour the observation stays."""
    by_hour: dict[datetime, SampleLike] = {}
    for s in samples:
        key = s.slot_time.replace(minute=0, second=0, microsecond=0)
        current = by_hour.get(key)
        if current is None or (current.kind != "observation" and s.kind == "observation"):
            by_hour[key] = s
    return [by_hour[k] for k in sorted(by_hour)]


def pick_condition(samples: Sequence[SampleLike], zone: tzinfo) -> str:
    daytime = [s for s in samples if _is_day(s, zone)] or list(samples)
    labels = [label_for(s.condition_code) for s in daytime]
    for significant in SIGNIFICANT:
        if significant in labels:
            return significant
    counts = Counter(label for label in labels if label in ("cloudy", "clear"))
    if not counts:
        return "unknown"
    cloudy, clear = counts.get("cloudy", 0), counts.get("clear", 0)
    return "cloudy" if cloudy >= clear else "clear"


def summarize_day(day: date, samples: Sequence[SampleLike], zone: tzinfo) -> DaySummary:
    rows = dedupe_observation_over_forecast(samples)
    temps = [float(s.temp) for s in rows]
    mins = [float(s.temp_min) for s in rows]
    maxs = [float(s.temp_max) for s in rows]
    observed = sum(1 for s in rows if s.kind == "observation")
    return DaySummary(
        date=day,
        temp_avg=round(sum(temps) / len(temps), 1),
        temp_min=round(min(mins), 1),
        temp_max=round(max(maxs), 1),
        condition=pick_condition(rows, zone),
        observed_samples=observed,
        forecast_samples=len(rows) - observed,
        partial=len(rows) < expected_slots(day, zone),
    )


def group_by_local_day(samples: Sequence[SampleLike], zone: tzinfo) -> dict[date, list[SampleLike]]:
    groups: dict[date, list[SampleLike]] = {}
    for s in samples:
        groups.setdefault(local_day(s.slot_time, zone), []).append(s)
    return groups


def summarize(
    samples: Sequence[SampleLike], zone: tzinfo, today: date, days: int = 5
) -> tuple[DaySummary | None, list[DaySummary]]:
    """today's summary (None when no sample falls on it) and the next `days` local days."""
    groups = group_by_local_day(samples, zone)
    today_summary = summarize_day(today, groups[today], zone) if today in groups else None
    upcoming = []
    for offset in range(1, days + 1):
        day = today + timedelta(days=offset)
        if day in groups:
            upcoming.append(summarize_day(day, groups[day], zone))
        else:
            upcoming.append(
                DaySummary(day, float("nan"), float("nan"), float("nan"), "unknown", 0, 0, True)
            )
    return today_summary, upcoming
