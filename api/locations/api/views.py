"""Locations (L1): list, create, detail, update, deactivate, soft delete; weather by id (04 §2)."""

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core import settings_store
from core.permissions import ReadAnyWriteOps
from weather import adhoc, forecast, samples
from weather.api.serializers import CurrentWeatherSerializer, ForecastSerializer

from .. import brackets, services
from ..models import Location
from .serializers import BracketEdgesSerializer, LocationSerializer


class LocationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LocationSerializer
    permission_classes = [ReadAnyWriteOps]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

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
        summary="Locations grouped by current temperature bracket",
        description=(
            "Every active location with an observation appears in exactly one half-open bracket "
            "(lower edge included, upper excluded; open ended below the first and at or above "
            "the last edge). Fixed mode uses the configured edges; quantile mode derives edges "
            "from the current temperatures so no bracket is empty. Locations without an "
            "observation yet are listed under no_data. Served from stored samples; no upstream "
            "call."
        ),
        parameters=[
            OpenApiParameter("mode", str, description="fixed (default) or quantile"),
            OpenApiParameter("buckets", int, description="quantile mode: bracket count, default 4"),
        ],
    )
    @action(detail=False, methods=["get"], url_path="brackets")
    def brackets(self, request: Request) -> Response:
        mode = request.query_params.get("mode", "fixed")
        if mode not in ("fixed", "quantile"):
            raise serializers.ValidationError({"mode": "fixed or quantile."})
        try:
            requested = int(request.query_params.get("buckets", 4))
        except ValueError as exc:
            raise serializers.ValidationError({"buckets": "An integer."}) from exc
        if not 2 <= requested <= 10:
            raise serializers.ValidationError({"buckets": "Between 2 and 10."})

        locations = list(
            Location.objects.filter(active=True, deleted_at__isnull=True).order_by("name")
        )
        latest = samples.latest_observations_for(locations)
        now = timezone.now()
        stale_after = timedelta(seconds=2 * int(settings.REFRESH_INTERVAL_S))
        rows: list[dict[str, Any]] = []
        no_data: list[dict[str, Any]] = []
        for loc in locations:
            obs = latest.get(str(loc.pk))
            if obs is None:
                no_data.append({"id": str(loc.pk), "name": loc.name, "reason": "not refreshed yet"})
                continue
            rows.append(
                {
                    "id": str(loc.pk),
                    "name": loc.name,
                    "country_code": loc.country_code,
                    "temp": float(obs.temp),
                    "observed_at": obs.slot_time,
                    "stale": (now - obs.slot_time) > stale_after,
                }
            )
        if mode == "quantile":
            # Edges are reported to one decimal (L4.4); group on one-decimal temperatures too,
            # so a location never falls on the wrong side of its own rounded edge.
            for r in rows:
                r["temp"] = round(float(r["temp"]), 1)
            edges = brackets.quantile_edges([float(r["temp"]) for r in rows], requested)
            effective = len(edges) + 1 if rows else 0
        else:
            edges = settings_store.bracket_edges()
            effective = len(edges) + 1
        last_run = samples.last_finished_run()
        return Response(
            {
                "mode": mode,
                "edges": edges,
                "requested_buckets": requested if mode == "quantile" else None,
                "effective_buckets": effective,
                "refreshed_at": last_run.finished_at if last_run else None,
                "brackets": brackets.group(rows, edges),
                "no_data": no_data,
            }
        )

    @extend_schema(
        summary="Read or set the fixed bracket edges (ops writes)",
        request=BracketEdgesSerializer,
        responses={200: BracketEdgesSerializer},
    )
    @action(detail=False, methods=["get", "put"], url_path="bracket-edges")
    def bracket_edges(self, request: Request) -> Response:
        if request.method == "PUT":
            body = BracketEdgesSerializer(data=request.data)
            body.is_valid(raise_exception=True)
            try:
                edges = settings_store.set(
                    settings_store.BRACKET_EDGES, body.validated_data["edges"]
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict) from exc
            return Response({"edges": edges})
        return Response({"edges": settings_store.bracket_edges()})

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
