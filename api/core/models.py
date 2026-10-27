"""Core models: the shared base class, partners and the custom user with its role.

The user model is defined before the first migration, as Django requires
(AUTH_USER_MODEL = "core.User"). Roles and the partner rule follow 00-domain §5 and the
constraints table of 03-data-model.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class TimeStampedModel(models.Model):
    """UUID primary key plus created_at and updated_at, inherited by every table (N2.3, N2.4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Partner(TimeStampedModel):
    """A partner agency whose systems call the API with their own tokens.

    Lives in core because the user points at it; bookings and travellers reference it from
    the booking app (02 §5.2 dependency rule: booking -> core, never the reverse).
    """

    name = models.TextField(unique=True)
    is_demo = models.BooleanField(
        default=False, help_text="The case study site's partner; at most one row (A17)."
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_demo"], condition=Q(is_demo=True), name="partner_single_demo"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Role(models.TextChoices):
    OPS = "ops", "Operations"
    SALES = "sales", "Sales"
    PARTNER = "partner", "Partner"
    FINANCE = "finance", "Finance"


class User(AbstractUser):
    """Django's user with one role and, for partner users, the partner they act for."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.TextField(choices=Role.choices, default=Role.SALES)
    partner = models.ForeignKey(
        Partner, null=True, blank=True, on_delete=models.PROTECT, related_name="users"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=[r.value for r in Role]), name="user_role_valid"
            ),
            # partner_id is set exactly when the role is partner.
            models.CheckConstraint(
                condition=(Q(role=Role.PARTNER, partner__isnull=False))
                | (~Q(role=Role.PARTNER) & Q(partner__isnull=True)),
                name="user_partner_iff_role_partner",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
