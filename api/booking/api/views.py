"""Travellers and bookings (04 §7, P6, N6.2). Scope is applied in the queryset: a partner's
request never sees another partner's rows (404), and partner_id comes from the token."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .. import services
from ..models import Booking, Traveller
from ..permissions import BookingPermission, TravellerPermission
from .serializers import BookingCreateSerializer, BookingSerializer, TravellerSerializer


class TravellerViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """GET, POST /travellers?q=; GET, PATCH /travellers/{id}."""

    queryset = Traveller.objects.none()  # schema: the real scope comes from get_queryset
    serializer_class = TravellerSerializer
    permission_classes = [TravellerPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):  # noqa: ANN201
        qs = services.travellers_for(self.request.user)
        if self.action == "list" and (q := self.request.query_params.get("q")):
            qs = qs.filter(name__icontains=q)
        return qs

    @extend_schema(summary="Create a traveller; a partner's traveller belongs to that partner")
    def create(self, request: Request) -> Response:
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            traveller = services.create_traveller(request.user, dict(ser.validated_data))  # type: ignore[arg-type]
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return Response(self.get_serializer(traveller).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        summary="Bookings, newest first; partners see their own",
        parameters=[
            OpenApiParameter("departure", str),
            OpenApiParameter("traveller", str),
            OpenApiParameter("status", str, description="confirmed or cancelled"),
            OpenApiParameter("from", str, description="departure date >=, YYYY-MM-DD"),
            OpenApiParameter("to", str, description="departure date <=, YYYY-MM-DD"),
        ],
    )
)
class BookingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /bookings, POST /bookings, GET /bookings/{id}, POST /bookings/{id}/cancel."""

    queryset = Booking.objects.none()  # schema: the real scope comes from get_queryset
    serializer_class = BookingSerializer
    permission_classes = [BookingPermission]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):  # noqa: ANN201
        qs = services.bookings_for(self.request.user)
        if self.action == "list":
            try:
                qs = services.filter_bookings(qs, dict(self.request.query_params.items()))
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict) from exc
        return qs

    @extend_schema(
        summary="Book seats on a departure (ops, sales, partner)",
        description=(
            "Header Idempotency-Key is required: the same key from the same caller returns the "
            "original booking (200) and books nothing new; the same key with a different body "
            "is 422. Seats beyond the remaining count are 409 with `remaining`. The booking "
            "keeps the price, currency and danger at booking time. A partner's booking carries "
            "its partner_id, taken from the token."
        ),
        request=BookingCreateSerializer,
        responses={201: BookingSerializer, 200: BookingSerializer},
        parameters=[
            OpenApiParameter("Idempotency-Key", str, OpenApiParameter.HEADER, required=True)
        ],
    )
    def create(self, request: Request) -> Response:
        ser = BookingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            booking, created = services.create_booking(
                request.user,  # type: ignore[arg-type]
                data["departure_id"],
                data["traveller_id"],
                data["seats"],
                request.headers.get("Idempotency-Key", ""),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        row = self.get_queryset().get(pk=booking.pk)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(self.get_serializer(row).data, status=code)

    @extend_schema(
        summary="Cancel a booking: frees the seats, keeps the record, idempotent",
        request=None,
        responses={200: BookingSerializer},
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        booking = services.cancel_booking(request.user, self.get_object())  # type: ignore[arg-type]
        row = self.get_queryset().get(pk=booking.pk)
        return Response(self.get_serializer(row).data)
