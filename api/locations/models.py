"""Location: a place on the map the agency cares about (L1, L2; 03-data-model).

Minimal here so that weather samples have something to point at; CRUD, seed, time zone
derivation and the delete guard arrive with B4.
"""

from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


class Location(TimeStampedModel):
    name = models.TextField()
    country_code = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    latitude = models.DecimalField(max_digits=8, decimal_places=5)
    longitude = models.DecimalField(max_digits=8, decimal_places=5)
    timezone = models.TextField(help_text="IANA zone name, e.g. America/Lima")
    active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "country_code"],
                condition=Q(deleted_at__isnull=True),
                name="location_name_country_unique_live",
            ),
            models.CheckConstraint(
                condition=Q(latitude__gte=-90, latitude__lte=90), name="location_latitude_range"
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180, longitude__lte=180),
                name="location_longitude_range",
            ),
            models.CheckConstraint(
                condition=Q(country_code__regex=r"^[A-Z]{2}$"), name="location_country_code_iso"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.country_code})"
