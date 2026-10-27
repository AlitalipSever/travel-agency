from rest_framework import serializers

from ..models import Location


class LocationSerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="IANA name; derived from the coordinates when omitted",
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "country_code",
            "latitude",
            "longitude",
            "timezone",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_country_code(self, value: str) -> str:
        value = value.upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Two letter ISO 3166-1 code.")
        return value


class BracketEdgesSerializer(serializers.Serializer):
    edges = serializers.ListField(child=serializers.FloatField(), min_length=1, max_length=10)
