"""P5.1 to P5.5 and N3.1 for GET /packages/bookable."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from booking.models import Booking, Traveller
from catalogue import services
from catalogue.models import Departure, Destination
from core.models import User

URL = "/api/v1/packages/bookable"
TODAY = date.today()


def _d(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


def _package(name: str, destinations, price=1000, duration=7, active=True):  # noqa: ANN001, ANN201
    pkg = services.create_package(
        {"name": name, "price": price, "currency": "EUR", "duration_days": duration},
        [d.pk for d in destinations],
    )
    if not active:
        pkg.active = False
        pkg.save()
    return pkg


def _dep(pkg, days: int, capacity: int = 10, booked: int = 0) -> Departure:  # noqa: ANN001
    dep = services.create_departure(pkg, TODAY + timedelta(days=days), capacity)
    if booked:
        Booking.objects.create(
            departure=dep,
            traveller=Traveller.objects.create(name="T"),
            created_by=User.objects.get(username="u-ops"),
            seats=booked,
            price_at_booking=1,
            currency="EUR",
            danger_at_booking=0,
            idempotency_key=f"k{dep.pk}",
        )
    return dep


def _names(client, q: str) -> list[str]:  # noqa: ANN001
    r = client.get(f"{URL}?{q}")
    assert r.status_code == 200, r.content
    return [p["name"] for p in r.json()["results"]]


@pytest.mark.django_db
def test_p5_1_input_rules(ops) -> None:  # noqa: ANN001
    bad = [
        "to=2030-01-31&danger=1",  # from missing
        "from=2030-01-01&danger=1",  # to missing
        "from=2030-01-01&to=2030-01-31",  # danger missing
        "from=2030-01-31&to=2030-01-01&danger=1",  # from after to
        "from=2030-01-01&to=2031-01-03&danger=1",  # 367 days
        "from=2030-01-01&to=2030-01-31&danger=4",
        "from=2030-01-01&to=2030-01-31&danger=x",
        "from=2030-01-01&to=2030-01-31&danger=1&danger_mode=maybe",
        "from=soon&to=2030-01-31&danger=1",
    ]
    for q in bad:
        r = ops.get(f"{URL}?{q}")
        assert r.status_code == 400, q
        assert r["Content-Type"].startswith("application/problem+json")
    r = ops.get(f"{URL}?from=2030-01-01&to=2031-01-02&danger=1")  # exactly 366 days
    assert r.status_code == 200 and r.json()["query"]["danger_mode"] == "at_most"
    assert r.json()["query"]["timezone"] == "America/Lima"


@pytest.mark.django_db
def test_p5_2_every_condition_excludes_on_its_own(ops, old_town, death_road, lima, types) -> None:  # noqa: ANN001
    _dep(_package("Fits", [old_town, death_road]), 10)  # danger 2, planned, seats
    _dep(_package("Inactive", [old_town], active=False), 10)
    _dep(_package("Draft", []), 10)  # danger null
    high = Destination.objects.create(
        location=lima, type=types["adventure"], name="Volcano", danger=3
    )
    _dep(_package("Too dangerous", [high]), 10)
    _dep(_package("Outside range", [old_town]), 40)
    _dep(_package("Yesterday", [old_town]), -1)
    _dep(_package("Sold out", [old_town]), 10, capacity=5, booked=5)
    cancelled = _dep(_package("Cancelled", [old_town]), 10)
    services.cancel_departure(cancelled)

    assert _names(ops, f"from={_d(-5)}&to={_d(30)}&danger=2") == ["Fits"]


@pytest.mark.django_db
def test_p5_3_exact_mode(ops, old_town, death_road) -> None:  # noqa: ANN001
    _dep(_package("Low", [old_town]), 5)  # danger 0
    _dep(_package("Medium", [old_town, death_road]), 6)  # danger 2
    q = f"from={_d(0)}&to={_d(30)}"
    assert _names(ops, f"{q}&danger=2") == ["Low", "Medium"]
    assert _names(ops, f"{q}&danger=2&danger_mode=exact") == ["Medium"]
    assert _names(ops, f"{q}&danger=1&danger_mode=exact") == []


@pytest.mark.django_db
def test_p5_4_only_matching_departures_with_seats_and_end_date(ops, old_town) -> None:  # noqa: ANN001
    pkg = _package("Andes", [old_town], duration=7)
    _dep(pkg, 10, capacity=12, booked=10)  # matches: 2 left
    _dep(pkg, 20, capacity=4, booked=4)  # sold out: hidden
    _dep(pkg, 50)  # outside the range: hidden
    r = ops.get(f"{URL}?from={_d(0)}&to={_d(30)}&danger=1").json()
    assert r["count"] == 1
    deps = r["results"][0]["departures"]
    assert len(deps) == 1
    assert deps[0]["starts_on"] == _d(10) and deps[0]["ends_on"] == _d(16)
    assert deps[0] == {**deps[0], "capacity": 12, "confirmed_seats": 10, "remaining_seats": 2}
    assert r["results"][0]["danger_label"] == "none"


@pytest.mark.django_db
def test_p5_5_order_and_stable_pages(ops, old_town) -> None:  # noqa: ANN001
    _dep(_package("Zeta", [old_town]), 3)  # earliest departure first
    _dep(_package("Beta", [old_town]), 8)
    _dep(_package("Alpha", [old_town]), 8)  # same day as Beta: name decides
    _dep(_package("Alpha", [old_town]), 8)  # same name: id decides, stable
    q = f"from={_d(0)}&to={_d(30)}&danger=0"
    assert _names(ops, q) == ["Zeta", "Alpha", "Alpha", "Beta"]
    p1 = ops.get(f"{URL}?{q}&page_size=2").json()
    p2 = ops.get(f"{URL}?{q}&page_size=2&page=2").json()
    ids = [p["id"] for p in p1["results"]] + [p["id"] for p in p2["results"]]
    assert len(set(ids)) == 4 and p1["next"] and p2["previous"]


@pytest.mark.django_db
def test_n3_1_two_queries_per_page_plus_fixed_overhead(ops, old_town, death_road) -> None:  # noqa: ANN001
    for i in range(25):
        pkg = _package(f"P{i:02d}", [old_town, death_road])
        _dep(pkg, 5 + i % 7)
        _dep(pkg, 20 + i % 3)
    with CaptureQueriesContext(connection) as ctx:
        r = ops.get(f"{URL}?from={_d(0)}&to={_d(30)}&danger=2")
    assert r.status_code == 200 and len(r.json()["results"]) == 20
    # token, agency zone setting, count, packages, departures: 5 whatever the page holds
    assert len(ctx.captured_queries) <= 5, [q["sql"][:90] for q in ctx.captured_queries]
