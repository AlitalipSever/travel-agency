"""Per-token rate limit for ad hoc weather requests (W4.3, 04 §1).

Known locations are served from samples and never count. The rate comes from settings so
operations can tune it without a deploy of code (06 §8).
"""

from django.conf import settings
from rest_framework.throttling import UserRateThrottle


class AdHocWeatherThrottle(UserRateThrottle):
    scope = "adhoc_weather"

    def get_rate(self) -> str:
        return f"{int(settings.ADHOC_RATE_PER_MIN)}/min"
