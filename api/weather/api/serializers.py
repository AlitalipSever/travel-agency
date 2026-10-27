"""Query and response shapes for the weather endpoints (04 §2)."""

from rest_framework import serializers


class CoordinateQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

    def validate(self, attrs):  # noqa: ANN001, ANN201
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {k: "Unknown query parameter." for k in sorted(unknown)}
            )
        return attrs


class CurrentWeatherSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    timezone = serializers.CharField()
    temp = serializers.FloatField(help_text="degrees Celsius")
    condition = serializers.CharField()
    condition_code = serializers.IntegerField()
    humidity = serializers.IntegerField(allow_null=True)
    wind_speed = serializers.FloatField(allow_null=True)
    observed_at = serializers.DateTimeField()
    # "source" is also an attribute name on DRF fields; declared fields are collected by the
    # metaclass so this is safe at runtime, the stubs just cannot tell.
    source = serializers.ChoiceField(choices=["live", "cached", "stale", "sample"])  # type: ignore[assignment]
    age_s = serializers.IntegerField()
    location_id = serializers.UUIDField(allow_null=True)
