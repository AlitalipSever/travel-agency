"""Catalogue endpoints (04 §4): destination types, destinations, packages. Every role reads;
only ops writes. Rules live in services; the derived danger comes from the queryset."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import serializers, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import ReadAnyWriteOps

from .. import services
from ..models import Destination, DestinationType, Package
from .serializers import DestinationSerializer, DestinationTypeSerializer, PackageSerializer

_WRITE_METHODS = ["get", "post", "patch", "delete", "head", "options"]


def _bool_param(value: str | None) -> bool | None:
    if value is None:
        return None
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    return None


def _int_param(value: str | None, name: str, lo: int, hi: int) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)
    except ValueError as exc:
        raise serializers.ValidationError({name: "An integer."}) from exc
    if not lo <= number <= hi:
        raise serializers.ValidationError({name: f"Between {lo} and {hi}."})
    return number


class DestinationTypeViewSet(viewsets.ModelViewSet):
    """GET, POST /destination-types; PATCH, DELETE /destination-types/{id} (P2.3)."""

    queryset = DestinationType.objects.all()
    serializer_class = DestinationTypeSerializer
    permission_classes = [ReadAnyWriteOps]
    http_method_names = _WRITE_METHODS
    pagination_class = None

    @extend_schema(summary="Delete a type; 409 while destinations use it")
    def destroy(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        services.delete_destination_type(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        summary="Destinations",
        parameters=[
            OpenApiParameter("type", str, description="type key"),
            OpenApiParameter("danger_max", int, description="0 to 3"),
            OpenApiParameter("location", str, description="location id"),
            OpenApiParameter("active", bool, description="default true"),
            OpenApiParameter("q", str, description="name contains"),
        ],
    )
)
class DestinationViewSet(viewsets.ModelViewSet):
    """Destinations (P2): CRUD by ops, read by every role."""

    serializer_class = DestinationSerializer
    permission_classes = [ReadAnyWriteOps]
    http_method_names = _WRITE_METHODS

    def get_queryset(self):  # noqa: ANN201
        qs = Destination.objects.filter(deleted_at__isnull=True).select_related("location", "type")
        if self.action != "list":
            return qs
        params = self.request.query_params
        active = _bool_param(params.get("active", "true"))
        if active is not None:
            qs = qs.filter(active=active)
        if key := params.get("type"):
            qs = qs.filter(type__key=key)
        if (danger_max := _int_param(params.get("danger_max"), "danger_max", 0, 3)) is not None:
            qs = qs.filter(danger__lte=danger_max)
        if location := params.get("location"):
            qs = qs.filter(location_id=location)
        if q := params.get("q"):
            qs = qs.filter(name__icontains=q)
        return qs.order_by("name")

    @extend_schema(summary="Soft delete; 409 naming the packages that list the destination")
    def destroy(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        services.soft_delete_destination(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        summary="Packages with their derived danger",
        parameters=[
            OpenApiParameter("active", bool, description="default true"),
            OpenApiParameter("danger_max", int, description="0 to 3; drafts (null) excluded"),
            OpenApiParameter("type", str, description="contains a destination of this type"),
            OpenApiParameter("max_price", float, description="price per traveller at most"),
            OpenApiParameter("q", str, description="name contains"),
        ],
    ),
    retrieve=extend_schema(summary="Package detail with the ordered itinerary"),
)
class PackageViewSet(viewsets.ModelViewSet):
    """Packages (P1, P4): CRUD by ops, read by every role; danger derived in the query."""

    serializer_class = PackageSerializer
    permission_classes = [ReadAnyWriteOps]
    http_method_names = _WRITE_METHODS

    def get_queryset(self):  # noqa: ANN201
        qs = (
            Package.objects.live()
            .with_danger()
            .prefetch_related(
                "package_destinations__destination__type",
                "package_destinations__destination__location",
            )
        )
        if self.action != "list":
            return qs
        params = self.request.query_params
        active = _bool_param(params.get("active", "true"))
        if active is not None:
            qs = qs.filter(active=active)
        if (danger_max := _int_param(params.get("danger_max"), "danger_max", 0, 3)) is not None:
            qs = qs.filter(danger__lte=danger_max)
        if key := params.get("type"):
            qs = qs.filter(package_destinations__destination__type__key=key).distinct()
        if max_price := params.get("max_price"):
            try:
                ceiling = Decimal(max_price)
            except InvalidOperation as exc:
                raise serializers.ValidationError({"max_price": "A number."}) from exc
            qs = qs.filter(price__lte=ceiling)
        if q := params.get("q"):
            qs = qs.filter(name__icontains=q)
        return qs.order_by("name")

    def _fresh(self, package: Package) -> Package:
        return self.get_queryset().get(pk=package.pk)

    @extend_schema(summary="Create a package with its ordered destinations (ops)")
    def create(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        ids = data.pop("destination_ids", [])
        try:
            package = services.create_package(data, ids)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return Response(
            self.get_serializer(self._fresh(package)).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(summary="Update fields; destination_ids replaces the ordered list (ops)")
    def partial_update(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        package = self.get_object()
        serializer = self.get_serializer(package, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        ids = data.pop("destination_ids", None)
        try:
            services.update_package(package, data, ids)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return Response(self.get_serializer(self._fresh(package)).data)

    @extend_schema(summary="Soft delete; 409 once a departure has bookings (B7/B9)")
    def destroy(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        services.soft_delete_package(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
