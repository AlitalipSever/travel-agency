"""Circuit breaker for the weather upstream (W4.6, ADR 0005; Nygard's stability pattern).

closed: calls pass; failures are counted, a success resets the count.
open: after BREAKER_FAILURES consecutive failures, no call for BREAKER_COOLDOWN_S seconds.
half-open: when the cooldown ends the first caller gets one probe; success closes the breaker,
failure opens it again. State is in Redis so every pod and the worker see the same breaker.
Upstream rejections (bad key, bad request) do not count: waiting would not fix them.
"""

from __future__ import annotations

from django.conf import settings

from core.redis_client import redis_connection

FAILURES_KEY = "owm:breaker:failures"
OPEN_KEY = "owm:breaker:open"
PROBE_KEY = "owm:breaker:probe"


class BreakerOpen(Exception):
    """The breaker is open: do not call the upstream now."""


def state() -> str:
    r = redis_connection()
    if r.exists(OPEN_KEY):
        return "open"
    if r.exists(PROBE_KEY):
        return "half_open"
    return "closed"


def allow() -> bool:
    """May a call go out now? Grants one probe when the cooldown has just ended."""
    r = redis_connection()
    if r.exists(OPEN_KEY):
        return False
    failures = int(r.get(FAILURES_KEY) or 0)
    if failures < int(settings.BREAKER_FAILURES):
        return True
    # Cooldown over, failures still at the threshold: exactly one caller probes.
    return bool(r.set(PROBE_KEY, "1", nx=True, ex=int(settings.BREAKER_COOLDOWN_S)))


def record_success() -> None:
    r = redis_connection()
    r.delete(FAILURES_KEY, OPEN_KEY, PROBE_KEY)


def record_failure() -> None:
    r = redis_connection()
    r.delete(PROBE_KEY)
    failures = int(r.incr(FAILURES_KEY))
    if failures >= int(settings.BREAKER_FAILURES):
        r.set(OPEN_KEY, "1", ex=int(settings.BREAKER_COOLDOWN_S))


def snapshot() -> dict[str, object]:
    r = redis_connection()
    return {
        "state": state(),
        "consecutive_failures": int(r.get(FAILURES_KEY) or 0),
        "open_for_s": max(int(r.ttl(OPEN_KEY) or 0), 0),
        "threshold": int(settings.BREAKER_FAILURES),
        "cooldown_s": int(settings.BREAKER_COOLDOWN_S),
    }
