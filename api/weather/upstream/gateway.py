"""The one door to the weather upstream: breaker, budget, retries, then the client.

Views and tasks call fetch_current / fetch_forecast here and never the client directly, so the
rules of W4 live in a single place (02 §8.4).
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable

from django.conf import settings

from . import breaker, budget
from .budget import Share
from .client import UpstreamError, UpstreamRateLimited, UpstreamRejected, get_client
from .types import Forecast, Observation

log = logging.getLogger(__name__)

RETRY_BACKOFF_S = (0.2, 0.5)  # before the 2nd and the 3rd attempt, plus jitter


class BudgetExhausted(Exception):
    """This share has no call left in the current minute."""


def _guarded[T](call: Callable[[], T], share: Share) -> T:
    if not breaker.allow():
        raise breaker.BreakerOpen()
    attempts = 1 + int(settings.UPSTREAM_RETRIES)
    last: Exception | None = None
    for attempt in range(attempts):
        if not budget.acquire(share):
            raise BudgetExhausted(share)
        try:
            result = call()
        except UpstreamRejected:
            raise  # our fault (key, request): no retry, no breaker change
        except UpstreamRateLimited as exc:
            breaker.record_failure()
            raise exc  # the upstream disagrees with our budget: stop, do not retry
        except UpstreamError as exc:
            last = exc
            breaker.record_failure()
            if attempt < attempts - 1:
                pause = RETRY_BACKOFF_S[min(attempt, len(RETRY_BACKOFF_S) - 1)]
                time.sleep(pause + random.uniform(0, pause / 2))  # noqa: S311  jitter, not crypto
            continue
        breaker.record_success()
        return result
    assert last is not None
    raise last


def fetch_current(lat: float, lon: float, share: Share = "adhoc") -> Observation:
    client = get_client()
    return _guarded(lambda: client.fetch_current(lat, lon), share)


def fetch_forecast(lat: float, lon: float, share: Share = "adhoc") -> Forecast:
    client = get_client()
    return _guarded(lambda: client.fetch_forecast(lat, lon), share)


def snapshot() -> dict[str, object]:
    return {"budget": budget.snapshot(), "breaker": breaker.snapshot()}
