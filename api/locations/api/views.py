"""Locations (L1): list, create, detail, update, deactivate, soft delete; weather by id (04 §2)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import ReadAnyWriteOps
from weather import adhoc, forecast
from weather.api.serializers import CurrentWeatherSerializer, ForecastSerializer

from .. import services
from ..models import Location
from .serializers import LocationSerializer


class LocationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LocationSerializer
    permission_classes = [ReadAnyWriteOps]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):  # noqa: ANN201
        qs = Location.objects.filter(deleted_at__isnull=True)
        if self.action != "list":
            return qs  # detail, update, delete and weather work on inactive rows too
        active = self.request.query_params.get("active", "true").lower()
        if active in ("true", "1"):
            qs = qs.filter(active=True)
        elif active in ("false", "0"):
            qs = qs.filter(active=False)
        if country := self.request.query_params.get("country"):
            qs = qs.filter(country_code=country.upper())
        if q := self.request.query_params.get("q"):
            qs = qs.filter(name__icontains=q)
        return qs.order_by("name")

    @extend_schema(
        summary="Create a location; the time zone is derived when omitted; a refresh is queued"
    )
    def create(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            location = services.create_location(serializer.validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return Response(self.get_serializer(location).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer) -> None:  # noqa: ANN001
        data = serializer.validated_data
        if "timezone" in data or "latitude" in data or "longitude" in data:
            instance = serializer.instance
            lat = float(data.get("latitude", instance.latitude))
            lon = float(data.get("longitude", instance.longitude))
            try:
                data["timezone"] = services.resolve_timezone(
                    lat, lon, data.get("timezone") or instance.timezone
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict) from exc
        serializer.save()

    @extend_schema(summary="Soft delete; 409 while active destinations reference the location")
    def destroy(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        services.soft_delete(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        responses={200: CurrentWeatherSerializer}, summary="Current weather of a known location"
    )
    @action(detail=True, methods=["get"], url_path="weather/current")
    def weather_current(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        location = self.get_object()
        current = adhoc.get_current(float(location.latitude), float(location.longitude))
        return Response(CurrentWeatherSerializer(current.as_dict()).data)

    @extend_schema(
        responses={200: ForecastSerializer}, summary="Five day forecast of a known location"
    )
    @action(detail=True, methods=["get"], url_path="weather/forecast")
    def weather_forecast(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        location = self.get_object()
        data = forecast.get_forecast(float(location.latitude), float(location.longitude))
        return Response(ForecastSerializer(data).data)
