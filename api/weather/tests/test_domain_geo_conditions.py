"""Domain helpers: condition labels (W3.4) and coordinate geometry."""

import pytest

from weather.domain.conditions import LABELS, label_for
from weather.domain.geo import Point, cache_key, distance_m, nearest_within, offset_label


@pytest.mark.parametrize(
    ("code", "label"),
    [
        (200, "thunderstorm"),
        (300, "rain"),
        (500, "rain"),
        (600, "snow"),
        (741, "fog"),
        (800, "clear"),
        (801, "clear"),
        (802, "clear"),
        (803, "cloudy"),
        (804, "cloudy"),
        (999, "unknown"),
        (None, "unknown"),
    ],
)
def test_label_for(code: int | None, label: str) -> None:
    assert label_for(code) == label and label in LABELS


def test_distance_and_nearest() -> None:
    lima = Point(-12.046, -77.043)
    assert distance_m(lima, lima) == 0
    assert 90 < distance_m(lima, Point(-12.046, -77.0421)) < 110  # about 98 m east
    candidates = [("lima", lima), ("la_paz", Point(-16.4897, -68.1193))]
    assert nearest_within(Point(-12.0465, -77.043), candidates) == "lima"  # 55 m
    assert nearest_within(Point(-12.05, -77.043), candidates) is None  # 440 m


def test_cache_key_rounds_to_three_decimals() -> None:
    assert cache_key(-12.04612, -77.04349) == "-12.046,-77.043"
    assert cache_key(-12.0464, -77.0434) == cache_key(-12.0458, -77.0426)


def test_offset_label() -> None:
    assert offset_label(-18000) == "UTC-05:00"
    assert offset_label(19800) == "UTC+05:30"
    assert offset_label(0) == "UTC+00:00"
