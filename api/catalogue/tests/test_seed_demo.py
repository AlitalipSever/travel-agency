"""A17 / B12: the demo seed is idempotent and produces a sold-out departure for the walkthrough."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from catalogue.models import Departure, Package
from core.models import Partner, User
from locations.services import seed as seed_locations


@pytest.mark.django_db
def test_seed_demo_is_idempotent_and_has_a_sold_out_departure(types) -> None:  # noqa: ANN001
    seed_locations()
    out = StringIO()
    call_command("seed_demo", stdout=out)
    assert "demo-partner" in out.getvalue()
    counts = (Package.objects.count(), Departure.objects.count())
    call_command("seed_demo", stdout=StringIO())
    assert (Package.objects.count(), Departure.objects.count()) == counts
    assert Partner.objects.filter(is_demo=True).count() == 1
    assert User.objects.get(username="demo-partner").partner is not None
    sold_out = [d for d in Departure.objects.with_seats() if d.remaining_seats == 0]  # type: ignore[attr-defined]
    assert len(sold_out) == 1 and sold_out[0].package.name == "Andes adventure"
