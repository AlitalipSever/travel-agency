"""Read-only views of samples and runs for operations (06 §9)."""

from django.contrib import admin

from .models import RefreshRun, WeatherSample


@admin.register(WeatherSample)
class WeatherSampleAdmin(admin.ModelAdmin):
    list_display = (
        "location",
        "kind",
        "slot_time",
        "temp",
        "condition_code",
        "is_day",
        "fetched_at",
    )
    list_filter = ("kind", "location")
    date_hierarchy = "slot_time"
    readonly_fields = [f.name for f in WeatherSample._meta.fields]

    def has_add_permission(self, request) -> bool:  # noqa: ANN001
        return False


@admin.register(RefreshRun)
class RefreshRunAdmin(admin.ModelAdmin):
    list_display = (
        "started_at",
        "finished_at",
        "trigger",
        "locations",
        "calls_used",
        "failures",
        "effective_interval_s",
    )
    list_filter = ("trigger",)
    readonly_fields = [f.name for f in RefreshRun._meta.fields]

    def has_add_permission(self, request) -> bool:  # noqa: ANN001
        return False
