"""N6.1 groundwork: the role set and the partner rule are enforced by the database."""

import pytest
from django.db import IntegrityError

from core.models import Partner, Role, User


@pytest.mark.django_db
def test_partner_user_must_have_a_partner() -> None:
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="p1", password="x", role=Role.PARTNER, partner=None)


@pytest.mark.django_db
def test_non_partner_user_must_not_have_a_partner() -> None:
    partner = Partner.objects.create(name="Andes Tours")
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="s1", password="x", role=Role.SALES, partner=partner)


@pytest.mark.django_db
def test_only_one_demo_partner() -> None:
    Partner.objects.create(name="demo", is_demo=True)
    with pytest.raises(IntegrityError):
        Partner.objects.create(name="demo two", is_demo=True)


@pytest.mark.django_db
def test_unknown_role_is_rejected() -> None:
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="m1", password="x", role="marketing")
