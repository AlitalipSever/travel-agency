"""Booking tables (P6; 03-data-model): travellers and bookings. The tables arrive with B7 so
that departures can count confirmed seats; the booking rules (row lock, idempotency, partner
scope) and the endpoints arrive with B9. Dependency rule (02 §5.2): booking -> catalogue,
booking -> core, never the reverse.
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from catalogue.models import DANGER_MAX, DANGER_MIN, Departure
from core.models import Partner, TimeStampedModel


class Traveller(TimeStampedModel):
    """The person a booking is made for: a record, never a user (00-domain §5)."""

    partner = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="travellers",
        help_text="Null for the agency's own travellers.",
    )
    name = models.TextField()
    email = models.EmailField(blank=True, default="")
    risk_appetite = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(DANGER_MIN), MaxValueValidator(DANGER_MAX)],
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(risk_appetite__isnull=True)
                | Q(risk_appetite__gte=DANGER_MIN, risk_appetite__lte=DANGER_MAX),
                name="traveller_risk_appetite_0_3",
            )
        ]

    def __str__(self) -> str:
        return self.name


class BookingStatus(models.TextChoices):
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"


class CancelledBy(models.TextChoices):
    TRAVELLER_REQUEST = "traveller_request", "Traveller request"
    AGENCY = "agency", "Agency"
    DEPARTURE_CANCELLED = "departure_cancelled", "Departure cancelled"


class Booking(TimeStampedModel):
    """Seats on a departure with the price and danger at booking time (P6, P1.2, P4.5)."""

    departure = models.ForeignKey(Departure, on_delete=models.PROTECT, related_name="bookings")
    traveller = models.ForeignKey(Traveller, on_delete=models.PROTECT, related_name="bookings")
    partner = models.ForeignKey(
        Partner, null=True, blank=True, on_delete=models.PROTECT, related_name="bookings"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    seats = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    price_at_booking = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    danger_at_booking = models.PositiveSmallIntegerField()
    idempotency_key = models.TextField()
    status = models.TextField(choices=BookingStatus.choices, default=BookingStatus.CONFIRMED)
    cancelled_by = models.TextField(choices=CancelledBy.choices, null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(seats__gte=1), name="booking_seats_min_1"),
            models.CheckConstraint(
                condition=Q(price_at_booking__gte=0), name="booking_price_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in BookingStatus]),
                name="booking_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=BookingStatus.CANCELLED,
                        cancelled_by__isnull=False,
                        cancelled_at__isnull=False,
                    )
                )
                | (
                    ~Q(status=BookingStatus.CANCELLED)
                    & Q(cancelled_by__isnull=True, cancelled_at__isnull=True)
                ),
                name="booking_cancel_fields_iff_cancelled",
            ),
            models.UniqueConstraint(
                fields=["created_by", "idempotency_key"], name="booking_idempotency_per_user"
            ),
        ]
        indexes = [
            models.Index(
                fields=["departure"],
                condition=Q(status=BookingStatus.CONFIRMED),
                name="booking_dep_confirmed_idx",
            ),
            models.Index(fields=["partner", "created_at"], name="booking_partner_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.seats} seat(s) on {self.departure_id}"
