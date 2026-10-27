"""Coordinate helpers: validation bounds, rounding for cache keys, nearest known location."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

KNOWN_LOCATION_RADIUS_M = 100.0
EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True, slots=True)
class Point:
    lat: float
    lon: float


def distance_m(a: Point, b: Point) -> float:
    """Great-circle distance (Haversine); fine at the scale of a city."""
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dphi = phi2 - phi1
    dlambda = math.radians(b.lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def cache_key(lat: float, lon: float) -> str:
    """Three decimals (about 100 m): nearby requests share one cache entry (ADR 0005)."""
    return f"{round(lat, 3):.3f},{round(lon, 3):.3f}"


def nearest_within[T](
    point: Point, candidates: Iterable[tuple[T, Point]], radius_m: float = KNOWN_LOCATION_RADIUS_M
) -> T | None:
    best: tuple[float, T] | None = None
    for item, where in candidates:
        d = distance_m(point, where)
        if d <= radius_m and (best is None or d < best[0]):
            best = (d, item)
    return None if best is None else best[1]


def offset_label(offset_s: int) -> str:
    """UTC+05:30 style label for ad hoc coordinates, where no IANA name is known."""
    sign = "+" if offset_s >= 0 else "-"
    total = abs(offset_s) // 60
    return f"UTC{sign}{total // 60:02d}:{total % 60:02d}"
