"""A16 and L4.1, L4.2: settings have defaults, are validated, and apply on the next read."""

from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError

from core import settings_store as store
from core.models import Setting


@pytest.mark.django_db
def test_defaults_apply_when_no_row_exists() -> None:
    assert store.bracket_edges() == [10.0, 20.0, 25.0, 30.0]
    assert store.agency_timezone() == ZoneInfo("America/Lima")
    assert store.sample_retention_days() == 90


@pytest.mark.django_db
def test_set_applies_on_the_next_read() -> None:
    store.set(store.BRACKET_EDGES, [5, 15, 25])
    assert store.bracket_edges() == [5.0, 15.0, 25.0]
    store.set(store.AGENCY_TIMEZONE, "Europe/Berlin")
    assert store.agency_timezone() == ZoneInfo("Europe/Berlin")
    assert Setting.objects.count() == 2


@pytest.mark.parametrize(
    "value",
    [[], [1] * 11, [10, 10], [20, 10], ["a", "b"], "10,20"],
)
def test_bad_bracket_edges_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        store.validate(store.BRACKET_EDGES, value)


def test_bad_time_zone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        store.validate(store.AGENCY_TIMEZONE, "Mars/Olympus")


@pytest.mark.parametrize("value", [0, 4000, 3.5, True, "90"])
def test_bad_retention_is_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        store.validate(store.SAMPLE_RETENTION_DAYS, value)


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        store.validate("colour", "blue")
