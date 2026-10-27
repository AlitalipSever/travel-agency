"""P6.1, P6.3 to P6.6 and N6.2 over HTTP."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from booking.models import Booking, Traveller

BOOK = "/api/v1/bookings"
TRAV = "/api/v1/travellers"


def _traveller(client: APIClient, name: str = "Ana") -> str:
    r = client.post(TRAV, {"name": name, "risk_appetite": 2}, format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def _book(client: APIClient, departure, traveller: str, seats: int, key: str):  # noqa: ANN001, ANN201
    return client.post(
        BOOK,
        {"departure_id": str(departure.pk), "traveller_id": traveller, "seats": seats},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


@pytest.mark.django_db
def test_p6_1_seat_bounds_and_snapshots(sales, departure) -> None:  # noqa: ANN001
    t = _traveller(sales)
    r = _book(sales, departure, t, 2, "k1")
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["price_at_booking"] == "450.00" and body["currency"] == "EUR"
    assert body["danger_at_booking"] == 1 and body["status"] == "confirmed"
    assert body["departure"]["ends_on"] > body["departure"]["starts_on"]
    assert body["created_by"] == "u-sales" and body["partner_id"] is None

    r = _book(sales, departure, t, 2, "k2")  # only 1 left
    assert r.status_code == 409 and r.json()["remaining"] == 1
    assert r["Content-Type"].startswith("application/problem+json")
    assert _book(sales, departure, t, 0, "k3").status_code == 400
    assert _book(sales, departure, t, 1, "k4").status_code == 201
    assert _book(sales, departure, t, 1, "k5").status_code == 409  # sold out

    # P6.4 / P1.2: a later price change does not touch the booking
    departure.package.price = "999.00"
    departure.package.save()
    assert sales.get(f"{BOOK}/{body['id']}").json()["price_at_booking"] == "450.00"


@pytest.mark.django_db
def test_p6_3_idempotency_replay_and_mismatch(sales, ops, departure) -> None:  # noqa: ANN001
    t = _traveller(sales)
    first = _book(sales, departure, t, 1, "same")
    again = _book(sales, departure, t, 1, "same")
    assert first.status_code == 201 and again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert Booking.objects.count() == 1
    r = _book(sales, departure, t, 2, "same")  # same key, different body
    assert r.status_code == 422 and r.json()["type"].endswith("idempotency-mismatch")
    # the key is per caller: ops may reuse the same string
    t2 = _traveller(ops, "Ben")
    assert _book(ops, departure, t2, 1, "same").status_code == 201
    assert _book(sales, departure, t, 1, "").status_code == 400  # header required


@pytest.mark.django_db
def test_p6_5_cancel_frees_seats_and_is_idempotent(sales, ops, departure) -> None:  # noqa: ANN001
    t = _traveller(sales)
    booked = _book(sales, departure, t, 3, "full").json()
    assert _book(sales, departure, t, 1, "late").status_code == 409
    r = sales.post(f"{BOOK}/{booked['id']}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert r.json()["cancelled_by"] == "traveller_request"
    first_at = r.json()["cancelled_at"]
    again = sales.post(f"{BOOK}/{booked['id']}/cancel")
    assert again.status_code == 200 and again.json()["cancelled_at"] == first_at
    assert _book(sales, departure, t, 3, "retry").status_code == 201  # seats are free again
    # an ops cancellation is attributed to the agency
    other = Booking.objects.get(idempotency_key="retry")
    assert ops.post(f"{BOOK}/{other.pk}/cancel").json()["cancelled_by"] == "agency"
    assert Booking.objects.count() == 2  # records kept


@pytest.mark.django_db
def test_p6_6_n6_2_partner_scope_and_roles(partner_a, partner_b, finance, ops, departure) -> None:  # noqa: ANN001
    ta = _traveller(partner_a, "Ana A")
    tb = _traveller(partner_b, "Ben B")
    a = _book(partner_a, departure, ta, 1, "a1")
    assert a.status_code == 201 and a.json()["partner_id"] is not None
    assert partner_b.get(f"{BOOK}/{a.json()['id']}").status_code == 404
    assert partner_b.post(f"{BOOK}/{a.json()['id']}/cancel").status_code == 404
    assert partner_b.get(f"{TRAV}/{ta}").status_code == 404
    assert _book(partner_b, departure, ta, 1, "b-steals").status_code == 400  # not its traveller
    assert [b["id"] for b in partner_b.get(BOOK).json()["results"]] == []
    assert len(ops.get(BOOK).json()["results"]) == 1
    assert finance.get(BOOK).status_code == 200
    assert _book(finance, departure, tb, 1, "f1").status_code == 403
    assert finance.post(TRAV, {"name": "x"}, format="json").status_code == 403
    assert Traveller.objects.get(pk=ta).partner_id is not None


@pytest.mark.django_db
def test_booking_refused_on_cancelled_departure_and_draft(sales, departure) -> None:  # noqa: ANN001
    from catalogue import services as catalogue

    t = _traveller(sales)
    catalogue.update_package(departure.package, {}, [])
    assert _book(sales, departure, t, 1, "draft").status_code == 409
    catalogue.cancel_departure(departure)
    assert _book(sales, departure, t, 1, "cancelled").status_code == 409


@pytest.mark.django_db
def test_booking_list_filters(sales, departure) -> None:  # noqa: ANN001
    t = _traveller(sales)
    _book(sales, departure, t, 1, "x1")
    b = _book(sales, departure, t, 1, "x2").json()
    sales.post(f"{BOOK}/{b['id']}/cancel")
    assert len(sales.get(f"{BOOK}?status=cancelled").json()["results"]) == 1
    assert len(sales.get(f"{BOOK}?departure={departure.pk}").json()["results"]) == 2
    assert sales.get(f"{BOOK}?status=maybe").status_code == 400
