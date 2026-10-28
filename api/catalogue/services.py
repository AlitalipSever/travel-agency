"""Catalogue services (P1, P2, P4): package writes with the ordered itinerary, delete guards,
seed of the destination types. Views and the admin call these; nothing else writes the
catalogue.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone as dj_timezone

from core import settings_store
from core.errors import Conflict

from .models import (
    Departure,
    DepartureStatus,
    Destination,
    DestinationType,
    Package,
    PackageDestination,
)

log = logging.getLogger(__name__)

INITIAL_TYPES: tuple[tuple[str, str], ...] = (
    ("adventure", "Adventure"),
    ("cultural", "Cultural"),
    ("nature", "Nature"),
    ("urban", "Urban"),
    ("beach", "Beach"),
)


# --- destination types -------------------------------------------------------------------


def seed_destination_types() -> dict[str, int]:
    """P2.3: insert the initial types that are missing; never overwrite an edited label."""
    created = skipped = 0
    for key, label in INITIAL_TYPES:
        _, was_created = DestinationType.objects.get_or_create(key=key, defaults={"label": label})
        if was_created:
            created += 1
        else:
            skipped += 1
    return {"created": created, "skipped": skipped}


def delete_destination_type(dtype: DestinationType) -> None:
    """04 §4: refused (409) while destinations use the type; otherwise removed for good."""
    count = dtype.destinations.filter(deleted_at__isnull=True).count()
    if count:
        raise Conflict(
            f"{count} destination(s) use this type; change their type first.",
            data={"destinations": count},
        )
    dtype.delete()


# --- destinations ------------------------------------------------------------------------


def packages_using(destination: Destination) -> list[Package]:
    return list(
        Package.objects.live()
        .filter(package_destinations__destination=destination)
        .order_by("name")
        .distinct()
    )


def soft_delete_destination(destination: Destination) -> None:
    """P2.5: refused while any package lists it, naming the packages; otherwise hidden."""
    used_by = packages_using(destination)
    if used_by:
        names = ", ".join(p.name for p in used_by)
        raise Conflict(
            f"This destination is part of {len(used_by)} package(s): {names}. "
            "Remove it from them or deactivate it instead.",
            data={"packages": [{"id": str(p.pk), "name": p.name} for p in used_by]},
        )
    destination.deleted_at = dj_timezone.now()
    destination.active = False
    destination.save(update_fields=["deleted_at", "active", "updated_at"])


# --- packages ----------------------------------------------------------------------------


def _resolve_destinations(
    ids: Sequence[Any], already_in: set[Any] | None = None
) -> list[Destination]:
    """Validate the ordered id list (P1.3, P2.5) and return the rows in the given order."""
    if len(set(ids)) != len(ids):
        raise ValidationError({"destinations": "The same destination appears more than once."})
    rows = {d.pk: d for d in Destination.objects.filter(pk__in=ids, deleted_at__isnull=True)}
    missing = [str(i) for i in ids if i not in rows]
    if missing:
        raise ValidationError({"destinations": f"Unknown destination(s): {', '.join(missing)}."})
    kept = already_in or set()
    inactive = [str(i) for i in ids if not rows[i].active and i not in kept]
    if inactive:
        raise ValidationError(
            {"destinations": f"Inactive destination(s) cannot be added: {', '.join(inactive)}."}
        )
    return [rows[i] for i in ids]


def _write_itinerary(package: Package, destinations: Sequence[Destination]) -> None:
    package.package_destinations.all().delete()
    PackageDestination.objects.bulk_create(
        [
            PackageDestination(package=package, destination=d, position=i)
            for i, d in enumerate(destinations, start=1)
        ]
    )


@transaction.atomic
def create_package(data: dict[str, Any], destination_ids: Sequence[Any]) -> Package:
    """P1.1, P1.3: the package and its ordered itinerary in one transaction."""
    destinations = _resolve_destinations(destination_ids)
    package = Package.objects.create(**data)
    _write_itinerary(package, destinations)
    return package


@transaction.atomic
def update_package(
    package: Package, data: dict[str, Any], destination_ids: Sequence[Any] | None
) -> Package:
    """PATCH semantics of 04 §4: fields change in place; `destinations` replaces the whole
    ordered list. Inactive destinations already in the package may stay (P2.5)."""
    for field, value in data.items():
        setattr(package, field, value)
    package.full_clean(exclude=["destinations"])
    package.save()
    if destination_ids is not None:
        current = set(package.package_destinations.values_list("destination_id", flat=True))
        _write_itinerary(package, _resolve_destinations(destination_ids, already_in=current))
    return package


def soft_delete_package(package: Package) -> None:
    """P1.6: refused while any departure has bookings; otherwise hidden, bookings stay visible."""
    booked = package.departures.filter(bookings__isnull=False).distinct().count()
    if booked:
        raise Conflict(
            f"{booked} departure(s) of this package have bookings; deactivate it instead.",
            data={"departures_with_bookings": booked},
        )
    package.deleted_at = dj_timezone.now()
    package.active = False
    package.save(update_fields=["deleted_at", "active", "updated_at"])


# --- departures (P3) ---------------------------------------------------------------------


def _seats(departure: Departure) -> tuple[int, int]:
    """(confirmed, bookings of any status) read fresh from the database."""
    row = Departure.objects.with_seats().get(pk=departure.pk)
    return int(row.confirmed_seats), departure.bookings.count()  # type: ignore[attr-defined]


def create_departure(package: Package, starts_on: date, capacity: int) -> Departure:
    """P3.1: one departure per package and date (409 on a duplicate), capacity >= 1."""
    if package.departures.filter(starts_on=starts_on).exists():
        raise Conflict(
            f"{package.name} already departs on {starts_on.isoformat()}.",
            data={"starts_on": starts_on.isoformat()},
        )
    departure = Departure(package=package, starts_on=starts_on, capacity=capacity)
    departure.full_clean()
    departure.save()
    return departure


def update_departure(departure: Departure, data: dict[str, Any]) -> Departure:
    """P3.3: capacity never below confirmed seats; the date moves only without bookings;
    a cancelled departure is frozen."""
    if departure.status == DepartureStatus.CANCELLED:
        raise Conflict("A cancelled departure cannot be changed.")
    confirmed, any_bookings = _seats(departure)
    if "capacity" in data and data["capacity"] < confirmed:
        raise Conflict(
            f"Capacity cannot go below the {confirmed} confirmed seat(s).",
            data={"confirmed_seats": confirmed, "requested_capacity": data["capacity"]},
        )
    if "starts_on" in data and data["starts_on"] != departure.starts_on and any_bookings:
        raise Conflict("The date cannot change while the departure has bookings.")
    if "starts_on" in data and (
        departure.package.departures.exclude(pk=departure.pk)
        .filter(starts_on=data["starts_on"])
        .exists()
    ):
        raise Conflict(f"{departure.package.name} already departs on {data['starts_on']}.")
    for field, value in data.items():
        setattr(departure, field, value)
    departure.full_clean()
    departure.save()
    return departure


def delete_departure(departure: Departure) -> None:
    """P3.4: deleted only without bookings; otherwise 409 pointing at cancel."""
    if departure.bookings.exists():
        raise Conflict(
            "This departure has bookings; cancel it instead of deleting it.",
            data={"bookings": departure.bookings.count()},
        )
    departure.delete()


@transaction.atomic
def cancel_departure(departure: Departure) -> Departure:
    """P3.4: cancel the departure and its confirmed bookings (`departure_cancelled`) in one
    transaction under the row lock the booking path also takes; idempotent."""
    locked = Departure.objects.select_for_update().get(pk=departure.pk)
    if locked.status == DepartureStatus.CANCELLED:
        return locked
    now = dj_timezone.now()
    locked.status = DepartureStatus.CANCELLED
    locked.cancelled_at = now
    locked.save(update_fields=["status", "cancelled_at", "updated_at"])
    locked.bookings.filter(status="confirmed").update(
        status="cancelled", cancelled_by="departure_cancelled", cancelled_at=now, updated_at=now
    )
    return locked


def departure_summaries(package_ids: Sequence[Any]) -> dict[Any, dict[str, Any]]:
    """For each package: the next planned departure on or after today in the agency's zone
    (A16) with its remaining seats, and the planned count. One query for the whole list."""
    today = dj_timezone.now().astimezone(settings_store.agency_timezone()).date()
    rows = (
        Departure.objects.with_seats()
        .filter(package_id__in=package_ids, status=DepartureStatus.PLANNED, starts_on__gte=today)
        .order_by("package_id", "starts_on")
        .only("package_id", "starts_on", "capacity")
    )
    out: dict[Any, dict[str, Any]] = {}
    for r in rows:
        entry = out.setdefault(r.package_id, {"next": None, "planned_count": 0})
        entry["planned_count"] += 1
        if entry["next"] is None:
            entry["next"] = {
                "starts_on": r.starts_on.isoformat(),
                "remaining_seats": int(r.remaining_seats),  # type: ignore[attr-defined]
            }
    return out
