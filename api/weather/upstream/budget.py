"""Upstream call budget (W4.2, W4.3, ADR 0005): per minute shares, a monthly counter.

The per minute limit of the free tier is 60 (F2). We spend at most 80 % of it, split into a
refresh share (the scheduled worker) and an ad hoc share (requests for unknown coordinates), so
that neither can starve the other: a bulkhead. Counters live in Redis so that every api pod and
the worker count against the same budget.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from django.conf import settings

from core.redis_client import redis_connection

Share = Literal["refresh", "adhoc"]

MINUTE_KEY_TTL_S = 120
MONTH_KEY_TTL_S = 40 * 24 * 3600


def share_limit(share: Share) -> int:
    return int(
        settings.UPSTREAM_REFRESH_SHARE if share == "refresh" else settings.UPSTREAM_ADHOC_SHARE
    )


def _minute_key(share: Share, now: datetime) -> str:
    return f"owm:calls:{share}:{now:%Y%m%d%H%M}"


def _month_key(now: datetime) -> str:
    return f"owm:calls:month:{now:%Y%m}"


def acquire(share: Share, now: datetime | None = None) -> bool:
    """Take one call from the share's budget for this minute; False when it is spent."""
    now = now or datetime.now(tz=UTC)
    r = redis_connection()
    key = _minute_key(share, now)
    count = int(r.incr(key))
    if count == 1:
        r.expire(key, MINUTE_KEY_TTL_S)
    if count > share_limit(share):
        r.decr(key)
        return False
    month = _month_key(now)
    if int(r.incr(month)) == 1:
        r.expire(month, MONTH_KEY_TTL_S)
    return True


def used(share: Share, now: datetime | None = None) -> int:
    now = now or datetime.now(tz=UTC)
    return int(redis_connection().get(_minute_key(share, now)) or 0)


def used_this_month(now: datetime | None = None) -> int:
    now = now or datetime.now(tz=UTC)
    return int(redis_connection().get(_month_key(now)) or 0)


def snapshot(now: datetime | None = None) -> dict[str, object]:
    now = now or datetime.now(tz=UTC)
    return {
        "minute": {
            share: {"used": used(share, now), "limit": share_limit(share)}
            for share in ("refresh", "adhoc")
        },
        "month": {"used": used_this_month(now), "limit": int(settings.UPSTREAM_MONTHLY_LIMIT)},
    }
