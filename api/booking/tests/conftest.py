"""Fixtures: four role clients (two partners), a package with a departure of 3 seats."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from catalogue import services as catalogue
from catalogue.models import Departure, Destination, DestinationType
from catalogue.services import seed_destination_types
from core.models import Partner, Role, User
from locations.models import Location


def client_for(username: str, role: str, partner: Partner | None = None) -> APIClient:
    user = User.objects.create_user(username=username, password="x", role=role, partner=partner)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")
    return c


@pytest.fixture
def ops(db) -> APIClient:  # noqa: ANN001
    return client_for("u-ops", Role.OPS)


@pytest.fixture
def sales(db) -> APIClient:  # noqa: ANN001
    return client_for("u-sales", Role.SALES)


@pytest.fixture
def finance(db) -> APIClient:  # noqa: ANN001
    return client_for("u-finance", Role.FINANCE)


@pytest.fixture
def partner_a(db) -> APIClient:  # noqa: ANN001
    return client_for("u-partner-a", Role.PARTNER, Partner.objects.create(name="A"))


@pytest.fixture
def partner_b(db) -> APIClient:  # noqa: ANN001
    return client_for("u-partner-b", Role.PARTNER, Partner.objects.create(name="B"))


@pytest.fixture
def departure(db) -> Departure:  # noqa: ANN001
    lima = Location.objects.create(
        name="Lima", country_code="PE", latitude=-12.046, longitude=-77.043, timezone="America/Lima"
    )
    seed_destination_types()
    dest = Destination.objects.create(
        location=lima, type=DestinationType.objects.get(key="cultural"), name="Centre", danger=1
    )
    pkg = catalogue.create_package(
        {"name": "Lima weekend", "price": "450.00", "currency": "EUR", "duration_days": 3},
        [dest.pk],
    )
    return catalogue.create_departure(pkg, date.today() + timedelta(days=10), capacity=3)
