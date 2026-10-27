"""Catalogue in the admin: types, destinations and packages with the ordered itinerary (P1, P2)."""

from django.contrib import admin

from .models import Departure, Destination, DestinationType, Package, PackageDestination


@admin.register(DestinationType)
class DestinationTypeAdmin(admin.ModelAdmin):
    list_display = ("key", "label")
    search_fields = ("key", "label")


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "type", "danger", "active", "deleted_at")
    list_filter = ("type", "danger", "active")
    search_fields = ("name", "location__name")
    autocomplete_fields = ("location",)


class PackageDestinationInline(admin.TabularInline):
    model = PackageDestination
    extra = 0
    ordering = ("position",)
    autocomplete_fields = ("destination",)


class DepartureInline(admin.TabularInline):
    model = Departure
    extra = 0
    fields = ("starts_on", "capacity", "status", "cancelled_at")
    readonly_fields = ("status", "cancelled_at")
    ordering = ("starts_on",)


@admin.register(Departure)
class DepartureAdmin(admin.ModelAdmin):
    list_display = ("package", "starts_on", "capacity", "status", "cancelled_at")
    list_filter = ("status",)
    search_fields = ("package__name",)
    date_hierarchy = "starts_on"


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "currency", "duration_days", "active", "deleted_at")
    list_filter = ("active", "currency")
    search_fields = ("name",)
    inlines = [PackageDestinationInline, DepartureInline]
