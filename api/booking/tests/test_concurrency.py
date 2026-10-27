"""P6.2 (Q3): two concurrent bookings of the last seat: exactly one success, one conflict."""

from __future__ import annotations

import threading

import pytest
from django.db import connection

from booking import services
from booking.models import Booking, Traveller
from core.models import Role, User


@pytest.mark.django_db(transaction=True)
def test_p6_2_last_seat_goes_to_exactly_one_caller(departure) -> None:  # noqa: ANN001
    users = [
        User.objects.create_user(username=f"s{i}", password="x", role=Role.SALES) for i in range(2)
    ]
    traveller = Traveller.objects.create(name="T")
    departure.capacity = 1
    departure.save()
    results: list[str] = []
    barrier = threading.Barrier(2)

    def attempt(user: User, key: str) -> None:
        try:
            barrier.wait(timeout=5)
            services.create_booking(user, departure.pk, traveller.pk, 1, key)
            results.append("ok")
        except Exception as exc:  # noqa: BLE001
            results.append(type(exc).__name__)
        finally:
            connection.close()

    for _round in range(20):
        Booking.objects.all().delete()
        results.clear()
        threads = [threading.Thread(target=attempt, args=(u, f"k{_round}")) for u in users]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert sorted(results) == ["Conflict", "ok"], results
        assert Booking.objects.filter(status="confirmed").count() == 1
