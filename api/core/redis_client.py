"""One shared Redis connection (weather budget and breaker, ad hoc cache, readiness).

Tests replace it with fakeredis through the `redis_connection` override.
"""

from __future__ import annotations

from functools import lru_cache

import redis
from django.conf import settings


@lru_cache(maxsize=1)
def redis_connection() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2.0)
