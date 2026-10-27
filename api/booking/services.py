"""Booking rules (P6; ADR 0002): seats under the departure row lock, idempotent create and
cancel, price and danger snapshots, partner ownership taken from the caller, never the body.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet, Sum
from django.utils import timezone as dj_timezone

from catalogue.models import Departure, DepartureStatus, Package
from core.errors import Conflict, IdempotencyMismatch
from core.models import Role, User

from .models import Booking, BookingStatus, CancelledBy, Traveller

log = logging.getLogger(__name__)


# --- scope -------------------------------------------------------------------------------


def bookings_for(user: User) -> QuerySet[Booking]:
    """P6.6, N6.2: partners see their own rows only; everyone else sees all."""
    qs = Booking.objects.select_related("departure__package", "traveller", "created_by").order_by(
        "-created_at", "-id"
    )
    if user.role == Role.PARTNER:
        return qs.filter(partner=user.partner)
    return qs


def travellers_for(user: User) -> QuerySet[Traveller]:
    qs = Traveller.objects.order_by("name", "id")
    if user.role == Role.PARTNER:
        return qs.filter(partner=user.partner)
    return qs


def create_traveller(user: User, data: dict[str, Any]) -> Traveller:
    """A partner's travellers belong to that partner; the agency's carry no partner."""
    partner = user.partner if user.role == Role.PARTNER else None
    traveller = Traveller(partner=partner, **data)
    traveller.full_clean()
    traveller.save()
    return traveller


# --- create ------------------------------------------------------------------------------


def _fingerprint(departure_id: Any, traveller_id: Any, seats: int) -> str:
    raw = json.dumps(
        {"departure": str(departure_id), "traveller": str(traveller_id), "seats": seats},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _confirmed_seats(departure: Departure) -> int:
    agg = departure.bookings.filter(status=BookingStatus.CONFIRMED).aggregate(s=Sum("seats"))
    return int(agg["s"] or 0)


@transaction.atomic
def create_booking(
    user: User, departure_id: Any, traveller_id: Any, seats: int, idempotency_key: str
) -> tuple[Booking, bool]:
    """Returns (booking, created). P6.1 seat bounds under the lock (P6.2), P6.3 replay and
    mismatch per caller, P6.4 price and danger snapshots, partner from the caller."""
    if not idempotency_key or len(idempotency_key) > 200:
        raise ValidationError({"Idempotency-Key": "Header required, at most 200 characters."})
    if seats < 1:
        raise ValidationError({"seats": "At least one seat."})

    fingerprint = _fingerprint(departure_id, traveller_id, seats)
    existing = Booking.objects.filter(created_by=user, idempotency_key=idempotency_key).first()
    if existing is not None:
        same = _fingerprint(existing.departure_id, existing.traveller_id, existing.seats)
        if same != fingerprint:
            raise IdempotencyMismatch(
                "This Idempotency-Key was already used with a different booking request."
            )
        return existing, False

    try:
        departure = (
            Departure.objects.select_for_update().select_related("package").get(pk=departure_id)
        )
    except (Departure.DoesNotExist, ValueError, TypeError) as exc:
        raise ValidationError({"departure_id": "Unknown departure."}) from exc
    traveller_qs = travellers_for(user)
    try:
        traveller = traveller_qs.get(pk=traveller_id)
    except (Traveller.DoesNotExist, ValueError, TypeError) as exc:
        raise ValidationError({"traveller_id": "Unknown traveller."}) from exc

    if departure.status != DepartureStatus.PLANNED:
        raise Conflict("This departure is cancelled.", data={"remaining": 0})
    package = departure.package
    if not package.active or package.deleted_at is not None:
        raise Conflict("This package is not on sale.", data={"remaining": 0})
    danger = Package.objects.with_danger().get(pk=package.pk).danger  # type: ignore[attr-defined]
    if danger is None:
        raise Conflict("This package is a draft without destinations.", data={"remaining": 0})

    remaining = departure.capacity - _confirmed_seats(departure)
    if seats > remaining:
        raise Conflict(
            f"Only {remaining} seat(s) left on this departure.",
            data={"remaining": remaining, "requested": seats},
        )

    booking = Booking.objects.create(
        departure=departure,
        traveller=traveller,
        partner=user.partner if user.role == Role.PARTNER else None,
        created_by=user,
        seats=seats,
        price_at_booking=package.price,
        currency=package.currency,
        danger_at_booking=int(danger),
        idempotency_key=idempotency_key,
    )
    log.info(
        "booking confirmed %s seats=%s departure=%s by=%s", booking.pk, seats, departure.pk, user.pk
    )
    return booking, True


# --- cancel ------------------------------------------------------------------------------


@transaction.atomic
def cancel_booking(user: User, booking: Booking) -> Booking:
    """P6.5: frees the seats (the row stays), idempotent; reason by the caller's role."""
    Departure.objects.select_for_update().filter(pk=booking.departure_id).exists()  # same lock
    locked = Booking.objects.select_for_update().get(pk=booking.pk)
    if locked.status == BookingStatus.CANCELLED:
        return locked
    locked.status = BookingStatus.CANCELLED
    locked.cancelled_by = (
        CancelledBy.AGENCY if user.role == Role.OPS else CancelledBy.TRAVELLER_REQUEST
    )
    locked.cancelled_at = dj_timezone.now()
    locked.save(update_fields=["status", "cancelled_by", "cancelled_at", "updated_at"])
    log.info("booking cancelled %s by=%s", locked.pk, user.pk)
    return locked


def filter_bookings(qs: QuerySet[Booking], params: dict[str, Any]) -> QuerySet[Booking]:
    """List filters of 04 §7: departure, traveller, status, from/to on the departure date."""
    if dep := params.get("departure"):
        qs = qs.filter(departure_id=dep)
    if trav := params.get("traveller"):
        qs = qs.filter(traveller_id=trav)
    if status_ := params.get("status"):
        if status_ not in (BookingStatus.CONFIRMED, BookingStatus.CANCELLED):
            raise ValidationError({"status": "confirmed or cancelled."})
        qs = qs.filter(status=status_)
    if start := params.get("from"):
        qs = qs.filter(departure__starts_on__gte=start)
    if end := params.get("to"):
        qs = qs.filter(departure__starts_on__lte=end)
    return qs
