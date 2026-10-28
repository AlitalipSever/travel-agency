"""Catalogue: destination types, destinations and packages (P1, P2, P4; 03-data-model).

A package's danger is never stored: it is derived from its destinations in the query
(ADR 0003), see ``PackageQuerySet.with_danger``. Soft delete follows the locations app.
"""

from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import DateField, ExpressionWrapper, F, Max, Q, Sum, Value
from django.db.models.functions import Coalesce

from core.models import TimeStampedModel
from locations.models import Location

DANGER_MIN = 0
DANGER_MAX = 3
DANGER_LABELS = {0: "none", 1: "low", 2: "medium", 3: "high"}
DESCRIPTION_MAX = 2000


def danger_label(score: int | None) -> str | None:
    """P4.3: none, low, medium, high; None for a draft without destinations."""
    return None if score is None else DANGER_LABELS[score]


class DestinationType(TimeStampedModel):
    """Reference list maintained by operations (P2.3): adventure, cultural, nature, ..."""

    key = models.SlugField(max_length=40, unique=True)
    label = models.TextField()

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class Destination(TimeStampedModel):
    """A place to visit inside a location, with a type and a danger score (P2)."""

    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="destinations")
    type = models.ForeignKey(DestinationType, on_delete=models.PROTECT, related_name="destinations")
    name = models.TextField()
    danger = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(DANGER_MIN), MaxValueValidator(DANGER_MAX)]
    )
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(
        default=True, help_text="False: cannot be added to new packages (P2.5)."
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(danger__gte=DANGER_MIN, danger__lte=DANGER_MAX),
                name="destination_danger_0_3",
            ),
            models.UniqueConstraint(
                fields=["location", "name"],
                condition=Q(deleted_at__isnull=True),
                name="destination_name_unique_per_location_live",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.location.name})"


class PackageQuerySet(models.QuerySet["Package"]):
    def live(self) -> PackageQuerySet:
        return self.filter(deleted_at__isnull=True)

    def with_danger(self) -> PackageQuerySet:
        """P4: the highest danger over all destinations, inactive included; null when none."""
        return self.annotate(danger=Max("package_destinations__destination__danger"))


class Package(TimeStampedModel):
    """A tour the agency sells: price per traveller, duration, ordered destinations (P1)."""

    name = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, help_text="ISO 4217, e.g. EUR")
    description = models.TextField(blank=True, default="", max_length=DESCRIPTION_MAX)
    duration_days = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    destinations = models.ManyToManyField(
        Destination, through="PackageDestination", related_name="packages"
    )

    objects = PackageQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="package_price_non_negative"),
            models.CheckConstraint(
                condition=Q(duration_days__gte=1), name="package_duration_min_1"
            ),
            models.CheckConstraint(
                condition=Q(currency__regex=r"^[A-Z]{3}$"), name="package_currency_iso"
            ),
        ]
        indexes = [models.Index(fields=["active"], name="package_active_idx")]

    def __str__(self) -> str:
        return self.name


class PackageDestination(models.Model):
    """One itinerary row: position starts at 1 and is unique within the package (P1.3)."""

    package = models.ForeignKey(
        Package, on_delete=models.CASCADE, related_name="package_destinations"
    )
    destination = models.ForeignKey(
        Destination, on_delete=models.PROTECT, related_name="package_destinations"
    )
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["package", "destination"], name="package_destination_once"
            ),
            models.UniqueConstraint(fields=["package", "position"], name="package_position_unique"),
        ]
        indexes = [models.Index(fields=["destination"], name="package_destination_dest_idx")]

    def __str__(self) -> str:
        return f"{self.package_id} #{self.position}"


class DepartureStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    CANCELLED = "cancelled", "Cancelled"


class DepartureQuerySet(models.QuerySet["Departure"]):
    def with_seats(self) -> DepartureQuerySet:
        """P3.2: confirmed and remaining seats from confirmed bookings, ends_on from the
        package duration (ADR 0002, ADR 0011). Nothing stored."""
        confirmed = Coalesce(
            Sum("bookings__seats", filter=Q(bookings__status="confirmed")), Value(0)
        )
        return self.annotate(
            confirmed_seats=confirmed,
            remaining_seats=F("capacity") - confirmed,
            ends_on=ExpressionWrapper(
                F("starts_on") + F("package__duration_days") - Value(1),
                output_field=DateField(),
            ),
        )


class Departure(TimeStampedModel):
    """One date on which a package runs, with its own capacity: the sellable unit (ADR 0002)."""

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="departures")
    starts_on = models.DateField()
    capacity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    status = models.TextField(choices=DepartureStatus.choices, default=DepartureStatus.PLANNED)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    objects = DepartureQuerySet.as_manager()

    class Meta:
        ordering = ["starts_on"]
        constraints = [
            models.UniqueConstraint(fields=["package", "starts_on"], name="departure_package_date"),
            models.CheckConstraint(condition=Q(capacity__gte=1), name="departure_capacity_min_1"),
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in DepartureStatus]),
                name="departure_status_valid",
            ),
            models.CheckConstraint(
                condition=(Q(status=DepartureStatus.CANCELLED, cancelled_at__isnull=False))
                | (~Q(status=DepartureStatus.CANCELLED) & Q(cancelled_at__isnull=True)),
                name="departure_cancelled_at_iff_cancelled",
            ),
        ]
        indexes = [
            models.Index(
                fields=["starts_on"],
                condition=Q(status=DepartureStatus.PLANNED),
                name="departure_planned_start_idx",
            ),
            # bookable search: the per-package probe "planned departure inside the range"
            # (P5.7, docs/plans/bookable.md); without it the planner walks the date index
            # and filters by package on every probe
            models.Index(
                fields=["package", "starts_on"],
                condition=Q(status=DepartureStatus.PLANNED),
                name="departure_pkg_planned_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.package_id} on {self.starts_on}"
