"""L1.2 time zone derivation and validation, L1.4 delete guard, L2 seed idempotence."""

import pytest
from django.core.exceptions import ValidationError

from locations import services
from locations.models import Location


@pytest.mark.parametrize(
    ("lat", "lon", "zone"),
    [
        (-12.046, -77.043, "America/Lima"),
        (-33.45, -70.66, "America/Santiago"),
        (-16.5, -68.15, "America/La_Paz"),
    ],
)
def test_derive_timezone_from_coordinates(lat: float, lon: float, zone: str) -> None:
    assert services.derive_timezone(lat, lon) == zone


def test_resolve_timezone_prefers_a_given_valid_name_and_rejects_bad_ones() -> None:
    assert services.resolve_timezone(-12.0, -77.0, "Europe/Berlin") == "Europe/Berlin"
    assert services.resolve_timezone(-12.0, -77.0, None) == "America/Lima"
    with pytest.raises(ValidationError):
        services.resolve_timezone(-12.0, -77.0, "Mars/Olympus")


@pytest.mark.django_db
def test_seed_is_idempotent_and_never_overwrites_edits() -> None:
    first = services.seed()
    assert first == {"created": 13, "skipped": 0}
    assert Location.objects.count() == 13
    lima = Location.objects.get(name="Lima")
    lima.latitude = -12.1
    lima.save()
    second = services.seed()
    assert second == {"created": 0, "skipped": 13}
    lima.refresh_from_db()
    assert float(lima.latitude) == -12.1
    assert not Location.objects.filter(name="Cayenne").exists()
    assert set(Location.objects.filter(country_code="BO").values_list("name", flat=True)) == {
        "Sucre",
        "La Paz",
    }


@pytest.mark.django_db(transaction=True)
def test_create_location_derives_zone_and_queues_a_refresh(monkeypatch) -> None:  # noqa: ANN001
    queued: list[str] = []
    monkeypatch.setattr(services, "_enqueue_refresh", lambda loc: queued.append(str(loc.pk)))
    loc = services.create_location(
        {"name": "Cusco", "country_code": "PE", "latitude": -13.5319, "longitude": -71.9675}
    )
    assert loc.timezone == "America/Lima"
    assert queued == [str(loc.pk)]  # on_commit fired: no transaction wraps a transactional test


@pytest.mark.django_db
def test_soft_delete_hides_but_keeps_the_row() -> None:
    loc = services.create_location(
        {"name": "Cusco", "country_code": "PE", "latitude": -13.5319, "longitude": -71.9675},
        refresh=False,
    )
    services.soft_delete(loc)
    loc.refresh_from_db()
    assert loc.deleted_at is not None and loc.active is False
    assert Location.objects.filter(pk=loc.pk).exists()
