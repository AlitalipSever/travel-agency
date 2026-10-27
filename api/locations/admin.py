"""Locations in the admin: the operations UI for the list (L1)."""

from django.contrib import admin

from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "country_code", "latitude", "longitude", "timezone", "active")
    list_filter = ("country_code", "active")
    search_fields = ("name",)
