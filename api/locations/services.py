"""Location services (L1, L2): time zone derivation, creation with the immediate refresh,
delete guard, seed. Views and the admin call these; nothing else writes locations.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone as dj_timezone

from core.errors import Conflict

from .models import Location

log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent / "data" / "capitals.json"


@lru_cache(maxsize=1)
def _finder():  # noqa: ANN202  timezonefinder loads its polygon data once per process
    from timezonefinder import TimezoneFinder

    return TimezoneFinder(in_memory=True)


def derive_timezone(latitude: float, longitude: float) -> str | None:
    """IANA zone for a coordinate from the offline polygon database (Etc/GMT zones at sea)."""
    return _finder().timezone_at(lat=latitude, lng=longitude)


def validate_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValidationError({"timezone": "Not an IANA time zone name."}) from exc
    return name


def resolve_timezone(latitude: float, longitude: float, given: str | None) -> str:
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise ValidationError({"latitude": "Coordinates out of range."})
    if given:
        return validate_timezone(given)
    derived = derive_timezone(latitude, longitude)
    if derived is None:
        raise ValidationError(
            {"timezone": "Could not derive a time zone for this coordinate; give one."}
        )
    return derived


def create_location(data: dict[str, Any], *, refresh: bool = True) -> Location:
    """Create and, after commit, refresh its weather at once (L1.5)."""
    data = dict(data)
    for key in ("latitude", "longitude"):
        data[key] = Decimal(str(round(float(data[key]), 5)))  # five decimals, about one metre
    data["timezone"] = resolve_timezone(
        float(data["latitude"]), float(data["longitude"]), data.get("timezone")
    )
    location = Location(**data)
    location.full_clean()
    location.save()
    if refresh:
        transaction.on_commit(lambda: _enqueue_refresh(location))
    return location


def _enqueue_refresh(location: Location) -> None:
    from weather.tasks import refresh_one_now

    refresh_one_now.delay(str(location.pk))


def active_destination_count(location: Location) -> int:
    """Destinations that still reference the location (the catalogue arrives with B6)."""
    related = getattr(location, "destinations", None)
    if related is None:
        return 0
    return related.filter(active=True, deleted_at__isnull=True).count()


def soft_delete(location: Location) -> None:
    """L1.4: refused while active destinations reference it; otherwise hidden, data kept."""
    count = active_destination_count(location)
    if count:
        raise Conflict(
            f"{count} active destination(s) reference this location; "
            "move or deactivate them first.",
            data={"active_destinations": count},
        )
    location.deleted_at = dj_timezone.now()
    location.active = False
    location.save(update_fields=["deleted_at", "active", "updated_at"])


def seed(path: Path = DATA_FILE) -> dict[str, int]:
    """L2: insert the capitals that are missing; never touch a row operations may have edited."""
    payload = json.loads(path.read_text())
    created = skipped = 0
    for row in payload["locations"]:
        exists = Location.objects.filter(
            name=row["name"], country_code=row["country_code"], deleted_at__isnull=True
        ).exists()
        if exists:
            skipped += 1
            continue
        Location.objects.create(
            name=row["name"],
            country_code=row["country_code"],
            latitude=Decimal(str(row["latitude"])),
            longitude=Decimal(str(row["longitude"])),
            timezone=validate_timezone(row["timezone"]),
        )
        created += 1
    log.info("seed_locations: created=%s skipped=%s", created, skipped)
    return {"created": created, "skipped": skipped}
