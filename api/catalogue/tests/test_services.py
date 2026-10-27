"""P1.3, P2.3, P2.5 and the type guard at the service level."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from catalogue import services
from catalogue.models import Destination, DestinationType, Package
from core.errors import Conflict

PKG = {"name": "Andes", "price": Decimal("1200.00"), "currency": "EUR", "duration_days": 7}


@pytest.mark.django_db
def test_p2_3_seed_is_idempotent() -> None:
    assert services.seed_destination_types() == {"created": 5, "skipped": 0}
    DestinationType.objects.filter(key="beach").update(label="Beach and coast")
    assert services.seed_destination_types() == {"created": 0, "skipped": 5}
    assert DestinationType.objects.get(key="beach").label == "Beach and coast"


@pytest.mark.django_db
def test_p1_3_itinerary_keeps_order_and_rejects_duplicates(old_town, death_road) -> None:  # noqa: ANN001
    pkg = services.create_package(PKG, [death_road.pk, old_town.pk])
    rows = list(pkg.package_destinations.order_by("position"))
    assert [(r.position, r.destination_id) for r in rows] == [
        (1, death_road.pk),
        (2, old_town.pk),
    ]
    with pytest.raises(ValidationError, match="more than once"):
        services.create_package(PKG, [old_town.pk, old_town.pk])
    assert Package.objects.count() == 1  # the failed create wrote nothing (transaction)


@pytest.mark.django_db
def test_p1_3_unknown_destination_is_rejected(old_town) -> None:  # noqa: ANN001
    import uuid

    with pytest.raises(ValidationError, match="Unknown destination"):
        services.create_package(PKG, [old_town.pk, uuid.uuid4()])


@pytest.mark.django_db
def test_p2_5_inactive_destination_not_addable_but_may_stay(old_town, death_road) -> None:  # noqa: ANN001
    pkg = services.create_package(PKG, [old_town.pk, death_road.pk])
    death_road.active = False
    death_road.save()
    # stays in the package when the list is rewritten
    services.update_package(pkg, {}, [death_road.pk, old_town.pk])
    assert list(pkg.package_destinations.values_list("destination_id", flat=True)) == [
        death_road.pk,
        old_town.pk,
    ]
    # cannot be added to a new package
    with pytest.raises(ValidationError, match="Inactive destination"):
        services.create_package({**PKG, "name": "Other"}, [death_road.pk])


@pytest.mark.django_db
def test_p2_5_delete_refused_while_listed_names_the_packages(old_town, death_road) -> None:  # noqa: ANN001
    services.create_package(PKG, [old_town.pk])
    services.create_package({**PKG, "name": "Coast"}, [old_town.pk])
    with pytest.raises(Conflict) as exc:
        services.soft_delete_destination(old_town)
    assert [p["name"] for p in exc.value.data["packages"]] == ["Andes", "Coast"]
    services.soft_delete_destination(death_road)  # unused: hidden, not removed
    row = Destination.objects.get(pk=death_road.pk)
    assert row.deleted_at is not None and row.active is False


@pytest.mark.django_db
def test_type_delete_refused_while_used(old_town, types) -> None:  # noqa: ANN001
    with pytest.raises(Conflict):
        services.delete_destination_type(types["cultural"])
    services.delete_destination_type(types["beach"])
    assert not DestinationType.objects.filter(key="beach").exists()


@pytest.mark.django_db
def test_update_package_replaces_fields_and_list(old_town, death_road) -> None:  # noqa: ANN001
    pkg = services.create_package(PKG, [old_town.pk])
    services.update_package(pkg, {"price": Decimal("1300.50")}, None)
    assert Package.objects.get(pk=pkg.pk).price == Decimal("1300.50")
    assert pkg.package_destinations.count() == 1  # None: list untouched
    services.update_package(pkg, {}, [])
    assert pkg.package_destinations.count() == 0  # empty list: draft
