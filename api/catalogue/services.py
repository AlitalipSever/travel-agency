"""Catalogue services (P1, P2, P4): package writes with the ordered itinerary, delete guards,
seed of the destination types. Views and the admin call these; nothing else writes the
catalogue.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone as dj_timezone

from core.errors import Conflict

from .models import Destination, DestinationType, Package, PackageDestination

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
    """P1.6: soft delete. The "departures with bookings" guard (409) joins with B7/B9."""
    package.deleted_at = dj_timezone.now()
    package.active = False
    package.save(update_fields=["deleted_at", "active", "updated_at"])
