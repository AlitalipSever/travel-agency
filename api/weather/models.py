"""What the worker fetches is kept (ADR 0012): samples per known location, and run summaries.

WeatherSample: one forecast slot or one observation, UTC, newest fetch wins per
(location, slot_time, kind). RefreshRun: one row per worker run for /ops/status and W4.2.
"""

import uuid

from django.db import models
from django.db.models import Q

from locations.models import Location


class SampleKind(models.TextChoices):
    FORECAST = "forecast", "Forecast"
    OBSERVATION = "observation", "Observation"


class WeatherSample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="samples")
    slot_time = models.DateTimeField(
        help_text="UTC; slot start for forecasts, instant for observations"
    )
    kind = models.CharField(max_length=11, choices=SampleKind.choices)
    fetched_at = models.DateTimeField()
    temp = models.DecimalField(max_digits=5, decimal_places=2)
    temp_min = models.DecimalField(max_digits=5, decimal_places=2)
    temp_max = models.DecimalField(max_digits=5, decimal_places=2)
    condition_code = models.IntegerField()
    condition_label = models.CharField(max_length=12, blank=True, default="")
    pop = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    is_day = models.BooleanField()
    raw = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["location", "slot_time", "kind"], name="weathersample_location_slot_kind"
            ),
            models.CheckConstraint(
                condition=Q(kind__in=[k.value for k in SampleKind]), name="weathersample_kind_valid"
            ),
            models.CheckConstraint(
                condition=Q(pop__isnull=True) | Q(pop__gte=0, pop__lte=1),
                name="weathersample_pop_range",
            ),
        ]
        indexes = [models.Index(fields=["location", "slot_time"], name="weathersample_loc_slot")]

    def __str__(self) -> str:
        return f"{self.location_id} {self.kind} {self.slot_time:%Y-%m-%d %H:%M}"


class RefreshTrigger(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    ON_CREATE = "on_create", "On location create"
    MANUAL = "manual", "Manual"


class RefreshRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    trigger = models.CharField(max_length=10, choices=RefreshTrigger.choices)
    locations = models.IntegerField(default=0)
    calls_used = models.IntegerField(default=0)
    failures = models.IntegerField(default=0)
    effective_interval_s = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["-started_at"], name="refreshrun_started")]

    def __str__(self) -> str:
        return f"{self.trigger} {self.started_at:%Y-%m-%d %H:%M} ({self.calls_used} calls)"
