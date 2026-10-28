"""Bookable packages search (P5, the brief's required endpoint).

Two queries per page, never one per package (N3.1): `packages(query)` selects and orders the
packages; `departures_for(ids, query)` fetches the matching departures of the page. Danger is
derived (ADR 0003), seats are derived (ADR 0002), the range applies to the departure date
(ADR 0011), "today" is the agency's local day (A16).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from django.core.exceptions import ValidationError
from django.db.models import Exists, F, Min, OuterRef, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone as dj_timezone

from core import settings_store

from .models import DANGER_MAX, DANGER_MIN, Departure, DepartureStatus, Package

MAX_SPAN_DAYS = 366
DangerMode = Literal["at_most", "exact"]


@dataclass(frozen=True, slots=True)
class SearchQuery:
    start: date
    end: date
    danger: int
    mode: DangerMode
    today: date
    timezone: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "from": self.start.isoformat(),
            "to": self.end.isoformat(),
            "danger": self.danger,
            "danger_mode": self.mode,
            "today": self.today.isoformat(),
            "timezone": self.timezone,
        }


def _date(value: str | None, name: str) -> date:
    if not value:
        raise ValidationError({name: "Required, YYYY-MM-DD."})
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({name: "A date, YYYY-MM-DD."}) from exc


def parse(params: dict[str, Any]) -> SearchQuery:
    """P5.1: from <= to, span at most 366 days, danger 0 to 3, mode at_most or exact."""
    start = _date(params.get("from"), "from")
    end = _date(params.get("to"), "to")
    if start > end:
        raise ValidationError({"to": "Must be on or after from."})
    if (end - start).days > MAX_SPAN_DAYS:
        raise ValidationError({"to": f"The range may span at most {MAX_SPAN_DAYS} days."})
    raw = params.get("danger")
    if raw is None or raw == "":
        raise ValidationError({"danger": "Required, 0 to 3."})
    try:
        danger = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"danger": "An integer, 0 to 3."}) from exc
    if not DANGER_MIN <= danger <= DANGER_MAX:
        raise ValidationError({"danger": f"Between {DANGER_MIN} and {DANGER_MAX}."})
    mode = params.get("danger_mode", "at_most")
    if mode not in ("at_most", "exact"):
        raise ValidationError({"danger_mode": "at_most or exact."})
    zone = settings_store.agency_timezone()
    today = dj_timezone.now().astimezone(zone).date()
    return SearchQuery(start, end, danger, mode, today, str(zone))


def _matching_departures(query: SearchQuery) -> QuerySet[Departure]:
    """Planned, inside the range, not before today, with seats left (P5.2)."""
    confirmed = Coalesce(Sum("bookings__seats", filter=Q(bookings__status="confirmed")), Value(0))
    return (
        Departure.objects.filter(
            status=DepartureStatus.PLANNED,
            starts_on__gte=max(query.start, query.today),
            starts_on__lte=query.end,
        )
        .annotate(confirmed=confirmed)
        .filter(capacity__gt=F("confirmed"))
    )


def packages(query: SearchQuery) -> QuerySet[Package]:
    """Query 1: the packages, ordered by earliest matching departure, name, id (P5.5)."""
    matching = _matching_departures(query).filter(package_id=OuterRef("pk"))
    first = (
        matching.order_by()
        .values("package_id")
        .annotate(first=Min("starts_on"))
        .values("first")[:1]
    )
    qs = Package.objects.live().with_danger().filter(active=True)
    if query.mode == "exact":
        qs = qs.filter(danger=query.danger)  # type: ignore[misc]  # annotation
    else:
        qs = qs.filter(danger__lte=query.danger)  # type: ignore[misc]  # null never matches
    return (
        qs.annotate(has_departure=Exists(matching), first_departure=first)
        .filter(has_departure=True)
        .order_by("first_departure", "name", "id")
    )


def departures_for(package_ids: Sequence[Any], query: SearchQuery) -> dict[Any, list[Departure]]:
    """Query 2: the matching departures of the page's packages, with seats and end date."""
    rows = (
        Departure.objects.with_seats()
        .filter(
            package_id__in=package_ids,
            status=DepartureStatus.PLANNED,
            starts_on__gte=max(query.start, query.today),
            starts_on__lte=query.end,
        )
        .filter(remaining_seats__gt=0)  # type: ignore[misc]  # annotation from with_seats()
        .order_by("starts_on", "id")
    )
    out: dict[Any, list[Departure]] = {pk: [] for pk in package_ids}
    for d in rows:
        out[d.package_id].append(d)
    return out
