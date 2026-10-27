"""Weather endpoints (04 §2): current weather for a coordinate (W1)."""

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import RateLimited

from .. import adhoc, forecast
from .serializers import CoordinateQuerySerializer, CurrentWeatherSerializer, ForecastSerializer
from .throttles import AdHocWeatherThrottle


class AdHocThrottleMixin:
    """Applies the per-token ad hoc limit (W4.3) with the headers of 04 §1."""

    def throttle_adhoc(self, request: Request) -> None:
        throttle = AdHocWeatherThrottle()
        if not throttle.allow_request(request, self):  # type: ignore[arg-type]
            wait = int(throttle.wait() or 60)
            raise RateLimited(
                "Too many ad hoc weather requests for this token.",
                headers={
                    "Retry-After": str(wait),
                    "X-RateLimit-Limit": str(int(settings.ADHOC_RATE_PER_MIN)),
                    "X-RateLimit-Remaining": "0",
                },
            )


class CurrentWeatherView(AdHocThrottleMixin, APIView):
    """GET /api/v1/weather/current?lat=&lon="""

    @extend_schema(
        parameters=[
            OpenApiParameter("lat", float, required=True, description="-90 to 90"),
            OpenApiParameter("lon", float, required=True, description="-180 to 180"),
        ],
        responses={200: CurrentWeatherSerializer},
        summary="Current weather for a coordinate",
        description=(
            "A coordinate within 100 m of a known location is answered from stored "
            "observations (source=sample). Any other coordinate goes through the ad hoc path: "
            "cached for 10 minutes, fetched live, served stale during an upstream outage, "
            "503 with Retry-After when nothing is stored. Ad hoc requests are rate limited per "
            "token."
        ),
    )
    def get(self, request: Request) -> Response:
        query = CoordinateQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        lat, lon = query.validated_data["lat"], query.validated_data["lon"]

        if adhoc.known_location(lat, lon) is None:
            self.throttle_adhoc(request)
        current = adhoc.get_current(lat, lon)
        return Response(CurrentWeatherSerializer(current.as_dict()).data)


class ForecastView(AdHocThrottleMixin, APIView):
    """GET /api/v1/weather/forecast?lat=&lon="""

    @extend_schema(
        parameters=[
            OpenApiParameter("lat", float, required=True, description="-90 to 90"),
            OpenApiParameter("lon", float, required=True, description="-180 to 180"),
        ],
        responses={200: ForecastSerializer},
        summary="Five day forecast for a coordinate",
        description=(
            "today plus five days from tomorrow in the location's local calendar. Each day: "
            "average, minimum and maximum temperature, a condition label, how many observed "
            "and forecast samples were used, and partial when slots are missing. Known "
            "locations are summarised from stored samples (today complete once samples "
            "exist); other coordinates go through the ad hoc path with the same cache, stale, "
            "429 and 503 behaviour as the current weather endpoint."
        ),
    )
    def get(self, request: Request) -> Response:
        query = CoordinateQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        lat, lon = query.validated_data["lat"], query.validated_data["lon"]
        if adhoc.known_location(lat, lon) is None:
            self.throttle_adhoc(request)
        return Response(ForecastSerializer(forecast.get_forecast(lat, lon)).data)
