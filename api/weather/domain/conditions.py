"""Upstream condition codes mapped to our closed label set (W3.4, ADR 0013).

OpenWeatherMap codes: 2xx thunderstorm, 3xx drizzle, 5xx rain, 6xx snow, 7xx atmosphere
(mist, fog, haze, dust...), 800 clear, 801 to 804 clouds. Codes 801 and 802 (few, scattered)
count as clear, 803 and 804 (broken, overcast) as cloudy. Anything else is unknown, never an
error. SIGNIFICANT is the precedence order for a day's label (W3.3).
"""

from __future__ import annotations

LABELS = ("thunderstorm", "rain", "snow", "fog", "cloudy", "clear", "unknown")
SIGNIFICANT = ("thunderstorm", "rain", "snow", "fog")


def label_for(code: int | None) -> str:
    if code is None:
        return "unknown"
    group = code // 100
    if group == 2:
        return "thunderstorm"
    if group in (3, 5):
        return "rain"
    if group == 6:
        return "snow"
    if group == 7:
        return "fog"
    if code == 800 or code in (801, 802):
        return "clear"
    if code in (803, 804):
        return "cloudy"
    return "unknown"
