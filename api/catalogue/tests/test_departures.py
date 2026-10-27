"""P3.1 to P3.6 and P1.6 over HTTP; bookings are written through the ORM (their rules are B9)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from booking.models import Booking, Traveller
from catalogue import services
from catalogue.models import Departure
from core.models import User

PKG = "/api/v1/packages"
DEP = "/api/v1/departures"
NEXT_YEAR = date.today().year + 1


@pytest.fixture
def package(old_town, death_road):  # noqa: ANN001, ANN201
    return services.create_package(
        {"name": "Andes", "price": 1200, "currency": "EUR", "duration_days": 7},
        [old_town.pk, death_road.pk],
    )


def _book(departure: Departure, seats: int, status: str = "confirmed") -> Booking:
    user = User.objects.get(username="u-ops")
    traveller = Traveller.objects.create(name="T")
    extra = {}
    if status == "cancelled":
        extra = {"cancelled_by": "agency", "cancelled_at": timezone.now()}
    return Booking.objects.create(
        departure=departure,
        traveller=traveller,
        created_by=user,
        seats=seats,
        price_at_booking=1200,
        currency="EUR",
        danger_at_booking=2,
        idempotency_key=f"k-{Booking.objects.count()}",
        status=status,
        **extra,
    )


def _add(ops, package, day: str, capacity: int = 12):  # noqa: ANN001, ANN201
    return ops.post(
        f"{PKG}/{package.pk}/departures",
        {"starts_on": day, "capacity": capacity},
        format="json",
    )


@pytest.mark.django_db
def test_p3_1_create_rules_and_roles(ops, sales, package) -> None:  # noqa: ANN001
    assert (
        sales.post(
            f"{PKG}/{package.pk}/departures",
            {"starts_on": "2030-01-01", "capacity": 5},
            format="json",
        ).status_code
        == 403
    )
    r = _add(ops, package, f"{NEXT_YEAR}-03-10")
    assert r.status_code == 201, r.content
    assert r.json()["ends_on"] == f"{NEXT_YEAR}-03-16"  # 7 day tour: 10th to 16th (ADR 0011)
    assert r.json()["confirmed_seats"] == 0 and r.json()["remaining_seats"] == 12
    assert _add(ops, package, f"{NEXT_YEAR}-03-10").status_code == 409  # one per package and date
    assert _add(ops, package, f"{NEXT_YEAR}-03-11", capacity=0).status_code == 400
    assert sales.get(f"{PKG}/{package.pk}/departures").status_code == 200


@pytest.mark.django_db
def test_p3_2_seats_count_only_confirmed_bookings(ops, package) -> None:  # noqa: ANN001
    dep_id = _add(ops, package, f"{NEXT_YEAR}-03-10").json()["id"]
    dep = Departure.objects.get(pk=dep_id)
    _book(dep, 3)
    _book(dep, 4)
    _book(dep, 5, status="cancelled")
    body = ops.get(f"{DEP}/{dep_id}").json()
    assert body["confirmed_seats"] == 7 and body["remaining_seats"] == 5


@pytest.mark.django_db
def test_p3_3_capacity_floor_at_confirmed_seats(ops, package) -> None:  # noqa: ANN001
    dep_id = _add(ops, package, f"{NEXT_YEAR}-03-10").json()["id"]
    _book(Departure.objects.get(pk=dep_id), 10)
    r = ops.patch(f"{DEP}/{dep_id}", {"capacity": 8}, format="json")
    assert r.status_code == 409 and r.json()["confirmed_seats"] == 10
    assert "10 confirmed" in r.json()["detail"]
    assert ops.patch(f"{DEP}/{dep_id}", {"capacity": 10}, format="json").status_code == 200
    r = ops.patch(f"{DEP}/{dep_id}", {"capacity": 20}, format="json")
    assert r.status_code == 200 and r.json()["remaining_seats"] == 10
    # the date is frozen while bookings exist
    assert (
        ops.patch(f"{DEP}/{dep_id}", {"starts_on": f"{NEXT_YEAR}-04-01"}, format="json").status_code
        == 409
    )


@pytest.mark.django_db
def test_p3_4_delete_only_without_bookings_cancel_otherwise(ops, package) -> None:  # noqa: ANN001
    free_id = _add(ops, package, f"{NEXT_YEAR}-03-10").json()["id"]
    booked_id = _add(ops, package, f"{NEXT_YEAR}-03-17").json()["id"]
    booked = Departure.objects.get(pk=booked_id)
    b1 = _book(booked, 2)
    b2 = _book(booked, 1, status="cancelled")

    assert ops.delete(f"{DEP}/{free_id}").status_code == 204
    assert not Departure.objects.filter(pk=free_id).exists()
    r = ops.delete(f"{DEP}/{booked_id}")
    assert r.status_code == 409 and "cancel" in r.json()["detail"]

    r = ops.post(f"{DEP}/{booked_id}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert r.json()["cancelled_at"] is not None
    b1.refresh_from_db()
    b2.refresh_from_db()
    assert b1.status == "cancelled" and b1.cancelled_by == "departure_cancelled"
    assert b2.cancelled_by == "agency"  # an earlier cancellation keeps its reason
    first = r.json()
    again = ops.post(f"{DEP}/{booked_id}/cancel")
    assert again.status_code == 200 and again.json()["cancelled_at"] == first["cancelled_at"]
    assert ops.patch(f"{DEP}/{booked_id}", {"capacity": 30}, format="json").status_code == 409


@pytest.mark.django_db
def test_p3_5_past_departures_stay_and_summary_skips_them(ops, package) -> None:  # noqa: ANN001
    past = (date.today() - timedelta(days=30)).isoformat()
    soon = (date.today() + timedelta(days=30)).isoformat()
    later = (date.today() + timedelta(days=60)).isoformat()
    for day in (past, later, soon):
        assert _add(ops, package, day).status_code == 201
    days = [d["starts_on"] for d in ops.get(f"{PKG}/{package.pk}/departures").json()]
    assert days == [past, soon, later]  # kept, ordered by date
    summary = ops.get(f"{PKG}/{package.pk}").json()["departures_summary"]
    assert summary == {"next": {"starts_on": soon, "remaining_seats": 12}, "planned_count": 2}
    listed = ops.get(PKG).json()["results"][0]["departures_summary"]
    assert listed["next"]["starts_on"] == soon


@pytest.mark.django_db
def test_departure_list_filters(ops, package) -> None:  # noqa: ANN001
    a = _add(ops, package, f"{NEXT_YEAR}-01-10").json()["id"]
    _add(ops, package, f"{NEXT_YEAR}-02-10")
    ops.post(f"{DEP}/{a}/cancel")
    base = f"{PKG}/{package.pk}/departures"
    assert len(ops.get(f"{base}?status=cancelled").json()) == 1
    assert len(ops.get(f"{base}?from={NEXT_YEAR}-02-01").json()) == 1
    assert len(ops.get(f"{base}?to={NEXT_YEAR}-01-31").json()) == 1
    assert ops.get(f"{base}?from=soon").status_code == 400
    assert ops.get(f"{base}?status=maybe").status_code == 400


@pytest.mark.django_db
def test_p1_6_package_with_booked_departure_is_not_deleted(ops, package) -> None:  # noqa: ANN001
    dep_id = _add(ops, package, f"{NEXT_YEAR}-03-10").json()["id"]
    _book(Departure.objects.get(pk=dep_id), 1)
    r = ops.delete(f"{PKG}/{package.pk}")
    assert r.status_code == 409 and r.json()["departures_with_bookings"] == 1
    r = ops.patch(f"{PKG}/{package.pk}", {"active": False}, format="json")
    assert r.status_code == 200 and r.json()["active"] is False
