"""Booking serializers (04 §7). Writes carry ids; reads carry the nested departure and
package summary and the snapshots taken at booking time."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from catalogue.models import DANGER_MAX, DANGER_MIN

from ..models import Booking, Traveller


class TravellerSerializer(serializers.ModelSerializer):
    risk_appetite = serializers.IntegerField(
        required=False, allow_null=True, min_value=DANGER_MIN, max_value=DANGER_MAX
    )

    class Meta:
        model = Traveller
        fields = ["id", "name", "email", "risk_appetite", "partner_id", "created_at", "updated_at"]
        read_only_fields = ["id", "partner_id", "created_at", "updated_at"]


class BookingCreateSerializer(serializers.Serializer):
    departure_id = serializers.UUIDField()
    traveller_id = serializers.UUIDField()
    seats = serializers.IntegerField(min_value=1)


class BookingSerializer(serializers.ModelSerializer):
    departure = serializers.SerializerMethodField()
    traveller = serializers.SerializerMethodField()
    created_by = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "departure",
            "traveller",
            "partner_id",
            "seats",
            "price_at_booking",
            "currency",
            "danger_at_booking",
            "status",
            "cancelled_by",
            "cancelled_at",
            "created_at",
            "created_by",
        ]
        read_only_fields = fields

    def get_departure(self, obj: Booking) -> dict[str, Any]:
        d = obj.departure
        return {
            "id": str(d.pk),
            "starts_on": d.starts_on.isoformat(),
            "ends_on": (
                d.starts_on.fromordinal(d.starts_on.toordinal() + d.package.duration_days - 1)
            ).isoformat(),
            "package": {"id": str(d.package_id), "name": d.package.name},
        }

    def get_traveller(self, obj: Booking) -> dict[str, Any]:
        return {"id": str(obj.traveller_id), "name": obj.traveller.name}
