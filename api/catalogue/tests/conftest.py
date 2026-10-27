"""Shared fixtures: role clients and a small catalogue (two locations, two types)."""

from __future__ import annotations

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from catalogue.models import Destination, DestinationType
from catalogue.services import seed_destination_types
from core.models import Role, User
from locations.models import Location


def _client(role: str) -> APIClient:
    user = User.objects.create_user(username=f"u-{role}", password="x", role=role)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")
    return c


@pytest.fixture
def ops(db) -> APIClient:  # noqa: ANN001
    return _client(Role.OPS)


@pytest.fixture
def sales(db) -> APIClient:  # noqa: ANN001
    return _client(Role.SALES)


@pytest.fixture
def lima(db) -> Location:  # noqa: ANN001
    return Location.objects.create(
        name="Lima", country_code="PE", latitude=-12.046, longitude=-77.043, timezone="America/Lima"
    )


@pytest.fixture
def la_paz(db) -> Location:  # noqa: ANN001
    return Location.objects.create(
        name="La Paz",
        country_code="BO",
        latitude=-16.5,
        longitude=-68.15,
        timezone="America/La_Paz",
    )


@pytest.fixture
def types(db) -> dict[str, DestinationType]:  # noqa: ANN001
    seed_destination_types()
    return {t.key: t for t in DestinationType.objects.all()}


@pytest.fixture
def old_town(lima: Location, types: dict[str, DestinationType]) -> Destination:
    return Destination.objects.create(
        location=lima, type=types["cultural"], name="Historic centre", danger=0
    )


@pytest.fixture
def death_road(la_paz: Location, types: dict[str, DestinationType]) -> Destination:
    return Destination.objects.create(
        location=la_paz, type=types["adventure"], name="Death Road ride", danger=2
    )
