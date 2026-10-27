"""Catalogue serializers (04 §4). Writes go through services; reads carry the derived danger."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from locations.models import Location

from ..models import (
    DANGER_MAX,
    DANGER_MIN,
    DESCRIPTION_MAX,
    Departure,
    Destination,
    DestinationType,
    Package,
    PackageDestination,
    danger_label,
)
from ..services import departure_summaries


class DestinationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationType
        fields = ["id", "key", "label", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LocationRefSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class DestinationSerializer(serializers.ModelSerializer):
    """Read: `type` key and `location {id, name}`; write: `location_id`, `type_id`."""

    location = LocationRefSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        source="location", queryset=Location.objects.all(), write_only=True
    )
    type: serializers.SlugRelatedField = serializers.SlugRelatedField(
        slug_field="key", read_only=True
    )
    type_id = serializers.PrimaryKeyRelatedField(
        source="type", queryset=DestinationType.objects.all(), write_only=True
    )
    danger = serializers.IntegerField(min_value=DANGER_MIN, max_value=DANGER_MAX)
    danger_label = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = [
            "id",
            "name",
            "location",
            "location_id",
            "type",
            "type_id",
            "danger",
            "danger_label",
            "description",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_danger_label(self, obj: Destination) -> str | None:
        return danger_label(obj.danger)

    def validate_location_id(self, value):  # noqa: ANN001, ANN201
        if value.deleted_at is not None:
            raise serializers.ValidationError("This location was deleted.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """P2.4: name unique within the location among live rows (the partial unique index
        is not seen by ModelSerializer's automatic validators)."""
        location = attrs.get("location", getattr(self.instance, "location", None))
        name = attrs.get("name", getattr(self.instance, "name", None))
        if location is not None and name is not None:
            clash = Destination.objects.filter(
                location=location, name=name, deleted_at__isnull=True
            )
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"name": "A destination with this name exists in this location."}
                )
        return attrs


class ItineraryRowSerializer(serializers.ModelSerializer):
    """One ordered stop inside a package representation (04 §4)."""

    id = serializers.UUIDField(source="destination.id", read_only=True)
    name = serializers.CharField(source="destination.name", read_only=True)
    type = serializers.CharField(source="destination.type.key", read_only=True)
    danger = serializers.IntegerField(source="destination.danger", read_only=True)
    active = serializers.BooleanField(source="destination.active", read_only=True)
    location = LocationRefSerializer(source="destination.location", read_only=True)

    class Meta:
        model = PackageDestination
        fields = ["position", "id", "name", "type", "danger", "active", "location"]


class PackageSerializer(serializers.ModelSerializer):
    """`danger` comes from the `with_danger()` annotation (ADR 0003); `destinations` is an
    ordered list of destination ids on write and the itinerary rows on read."""

    danger = serializers.IntegerField(read_only=True, allow_null=True)
    danger_label = serializers.SerializerMethodField()
    destinations = ItineraryRowSerializer(source="package_destinations", many=True, read_only=True)
    destination_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False, allow_empty=True
    )
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=DESCRIPTION_MAX
    )
    departures_summary = serializers.SerializerMethodField()

    class Meta:
        model = Package
        fields = [
            "id",
            "name",
            "price",
            "currency",
            "description",
            "duration_days",
            "active",
            "danger",
            "danger_label",
            "destinations",
            "destination_ids",
            "departures_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_danger_label(self, obj: Package) -> str | None:
        return danger_label(getattr(obj, "danger", None))

    def get_departures_summary(self, obj: Package) -> dict[str, Any]:
        """Next planned departure on or after today (agency zone) and the planned count; the
        view precomputes the map for a list so this costs one query, not one per package."""
        summaries = self.context.get("departure_summaries")
        if summaries is None:
            summaries = departure_summaries([obj.pk])
        return summaries.get(obj.pk, {"next": None, "planned_count": 0})

    def validate_currency(self, value: str) -> str:
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Three letter ISO 4217 code.")
        return value

    def validate_price(self, value: Any) -> Any:
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value


class DepartureSerializer(serializers.ModelSerializer):
    """Write: `starts_on`, `capacity`. Read adds the derived seats and `ends_on` (P3.2)."""

    package_id = serializers.UUIDField(source="package.id", read_only=True)
    ends_on = serializers.DateField(read_only=True)
    confirmed_seats = serializers.IntegerField(read_only=True)
    remaining_seats = serializers.IntegerField(read_only=True)
    capacity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Departure
        fields = [
            "id",
            "package_id",
            "starts_on",
            "ends_on",
            "capacity",
            "confirmed_seats",
            "remaining_seats",
            "status",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "cancelled_at", "created_at", "updated_at"]


class DeparturesSummarySerializer(serializers.Serializer):
    next = serializers.DictField(allow_null=True, read_only=True)
    planned_count = serializers.IntegerField(read_only=True)
