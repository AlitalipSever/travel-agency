"""W2.2, W3.1 to W3.5 (ADR 0013): the daily summary rules, table-tested on synthetic slots."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from weather.domain import summary

LIMA = ZoneInfo("America/Lima")  # UTC-5, no DST
SANTIAGO = ZoneInfo("America/Santiago")  # DST transitions


@dataclass
class S:
    slot_time: datetime
    kind: str = "forecast"
    temp: float = 20.0
    temp_min: float = 19.0
    temp_max: float = 21.0
    condition_code: int = 800
    is_day: bool | None = None


def day_slots(
    day: date, zone: ZoneInfo, codes: list[int], temps: list[float] | None = None
) -> list[S]:
    """Eight slots for a local day at 00, 03, ..., 21 local, with the given codes."""
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    out = []
    for i, code in enumerate(codes):
        t = (start + timedelta(hours=3 * i)).astimezone(UTC)
        temp = temps[i] if temps else 20.0
        out.append(
            S(
                slot_time=t,
                condition_code=code,
                temp=temp,
                temp_min=temp - 1,
                temp_max=temp + 1,
                is_day=(6 <= 3 * i < 18),
            )
        )
    return out


D = date(2026, 3, 10)


def test_slot_belongs_to_the_local_day_in_which_it_starts() -> None:
    # 21:00-24:00 Lima slot starts at 02:00 UTC next day; it is still the 10th in Lima.
    t = datetime(2026, 3, 11, 2, 0, tzinfo=UTC)
    assert summary.local_day(t, LIMA) == D
    assert summary.local_day(t, UTC) == date(2026, 3, 11)


def test_temperature_is_mean_min_max_to_one_decimal() -> None:
    slots = day_slots(D, LIMA, [800] * 8, temps=[10.04, 12, 14, 16, 18, 20, 22, 24.3])
    s = summary.summarize_day(D, slots, LIMA)
    assert (s.temp_avg, s.temp_min, s.temp_max) == (17.0, 9.0, 25.3)
    assert s.partial is False and s.forecast_samples == 8 and s.observed_samples == 0


@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        ([800] * 8, "clear"),
        ([803] * 8, "cloudy"),
        ([800, 800, 800, 500, 800, 800, 800, 800], "rain"),  # one daytime rain slot dominates
        ([800, 800, 200, 500, 600, 741, 800, 800], "thunderstorm"),  # precedence order
        ([800, 800, 600, 741, 800, 800, 800, 800], "snow"),
        ([800, 800, 741, 801, 802, 800, 800, 800], "fog"),
        ([500, 500, 800, 800, 801, 802, 500, 500], "clear"),  # rain only at night: ignored
        (
            [800, 800, 803, 804, 801, 802, 800, 800],
            "cloudy",
        ),  # 2 cloudy vs 2 clear daytime: tie -> cloudy
        ([800, 800, 803, 801, 802, 800, 800, 800], "clear"),  # 1 cloudy vs 3 clear
        ([800, 800, 999, 999, 999, 999, 800, 800], "unknown"),  # unmapped codes, no error
    ],
)
def test_condition_rules(codes: list[int], expected: str) -> None:
    assert summary.summarize_day(D, day_slots(D, LIMA, codes), LIMA).condition == expected


def test_without_daytime_slots_all_slots_count() -> None:
    slots = day_slots(D, LIMA, [500, 800, 800, 800, 800, 800, 800, 800])
    night_only = [s for s in slots if not s.is_day]  # 00, 03, 18, 21 local
    s = summary.summarize_day(D, night_only, LIMA)
    assert s.condition == "rain" and s.partial is True and s.forecast_samples == 4


def test_missing_is_day_mark_falls_back_to_06_18_local() -> None:
    slots = day_slots(D, LIMA, [500, 800, 800, 800, 800, 800, 800, 800])
    for s in slots:
        s.is_day = None
    assert summary.summarize_day(D, slots, LIMA).condition == "clear"  # rain at 00:00 is night


def test_observation_beats_forecast_for_the_same_hour() -> None:
    slots = day_slots(D, LIMA, [800] * 8)
    obs = S(
        slot_time=slots[4].slot_time,
        kind="observation",
        condition_code=500,
        temp=30,
        temp_min=30,
        temp_max=30,
        is_day=True,
    )
    s = summary.summarize_day(D, [*slots, obs], LIMA)
    assert s.condition == "rain" and s.observed_samples == 1 and s.forecast_samples == 7
    assert s.temp_max == 30.0  # the observation's values replaced the forecast slot's


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 3, 10), 8),
        (date(2026, 4, 4), 9),  # Chile leaves DST at 24:00 on the first Saturday of April: 25 h
        (date(2026, 9, 6), 7),  # Chile enters DST into the first Sunday of September: 23 h
    ],
)
def test_expected_slots_on_dst_days(day: date, expected: int) -> None:
    assert summary.expected_slots(day, SANTIAGO) == expected


def test_partial_when_slots_are_missing() -> None:
    slots = day_slots(D, LIMA, [800] * 8)[:5]
    assert summary.summarize_day(D, slots, LIMA).partial is True


def test_summarize_gives_today_and_five_days() -> None:
    all_slots: list[S] = []
    for offset in range(0, 6):
        all_slots += day_slots(D + timedelta(days=offset), LIMA, [800] * 8)
    all_slots = all_slots[3:-3]  # today starts at 09:00, the fifth day ends at 15:00
    today, days = summary.summarize(all_slots, LIMA, today=D)
    assert today is not None and today.partial is True and today.forecast_samples == 5
    assert [d.date for d in days] == [D + timedelta(days=i) for i in range(1, 6)]
    assert [d.partial for d in days] == [False, False, False, False, True]


def test_summarize_without_today_returns_none_and_empty_days_marked_partial() -> None:
    today, days = summary.summarize([], LIMA, today=D)
    assert today is None and len(days) == 5 and all(d.partial for d in days)
