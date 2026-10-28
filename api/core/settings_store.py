"""Typed access to the Setting table (A16, L4, 06 §8).

Known keys, their defaults and their validation live here; other apps call the readers and
never query the table directly. A missing row yields the default, so a fresh database works
before any seed.
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError

from .models import Setting

BRACKET_EDGES = "bracket_edges"
AGENCY_TIMEZONE = "agency_timezone"
SAMPLE_RETENTION_DAYS = "sample_retention_days"

DEFAULTS: dict[str, Any] = {
    BRACKET_EDGES: [10, 20, 25, 30],  # ADR 0004
    AGENCY_TIMEZONE: "America/Lima",  # assumption until the client says otherwise (A16)
    SAMPLE_RETENTION_DAYS: 90,  # ADR 0012
}


def validate(key: str, value: Any) -> Any:
    """Return the normalised value or raise ValidationError; used by the model and the API."""
    if key == BRACKET_EDGES:
        if not isinstance(value, list) or not 1 <= len(value) <= 10:
            raise ValidationError({key: "A list of 1 to 10 numbers."})
        try:
            edges = [float(v) for v in value]
        except (TypeError, ValueError) as exc:
            raise ValidationError({key: "Every edge must be a number."}) from exc
        if any(b <= a for a, b in zip(edges, edges[1:], strict=False)):
            raise ValidationError({key: "Edges must be strictly ascending."})
        return edges
    if key == AGENCY_TIMEZONE:
        try:
            ZoneInfo(str(value))
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise ValidationError({key: "Not an IANA time zone name."}) from exc
        return str(value)
    if key == SAMPLE_RETENTION_DAYS:
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 3650:
            raise ValidationError({key: "An integer between 1 and 3650 days."})
        return value
    raise ValidationError({"key": f"Unknown setting '{key}'."})


def get(key: str) -> Any:
    if key not in DEFAULTS:
        raise KeyError(key)
    row = Setting.objects.filter(key=key).first()
    return row.value if row is not None else DEFAULTS[key]


def set(key: str, value: Any) -> Any:  # noqa: A001  mirrors get(); the module is the namespace
    value = validate(key, value)
    Setting.objects.update_or_create(key=key, defaults={"value": value})
    return value


def bracket_edges() -> list[float]:
    return [float(v) for v in get(BRACKET_EDGES)]


def agency_timezone() -> ZoneInfo:
    return ZoneInfo(get(AGENCY_TIMEZONE))


def sample_retention_days() -> int:
    return int(get(SAMPLE_RETENTION_DAYS))
