"""N5.5: /ops/status reports the last run, the shares, the breaker and the cache counters."""

from datetime import UTC, datetime

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Role, User
from weather import samples, stats
from weather.models import RefreshTrigger
from weather.upstream import budget

URL = "/api/v1/ops/status"


def _client(role: str = Role.SALES) -> APIClient:
    user = User.objects.create_user(username=f"u-{role}", password="x", role=role)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")
    return c


@pytest.mark.django_db
def test_n5_5_status_reports_runs_shares_breaker_and_cache(fake_redis) -> None:  # noqa: ANN001
    assert APIClient().get(URL).status_code == 401
    run = samples.start_run(RefreshTrigger.MANUAL, 13)
    samples.finish_run(
        run, calls_used=26, failures=1, effective_interval_s=900, notes="one upstream error"
    )
    budget.acquire("refresh", datetime.now(tz=UTC))
    stats.record_adhoc("hit")
    stats.record_adhoc("hit")
    stats.record_adhoc("miss")

    body = _client().get(URL).json()
    assert body["last_run"]["run_id"] == str(run.pk)
    assert (
        body["last_finished_run"]["calls_used"] == 26 and body["last_finished_run"]["failures"] == 1
    )
    assert body["configured_interval_s"] == 900
    assert body["upstream"]["minute"]["refresh"] == {"used": 1, "limit": 40}
    assert body["upstream"]["month"]["used"] == 1
    assert body["breaker"]["state"] == "closed"
    assert body["adhoc_cache"] == {"hits": 2, "misses": 1, "hit_ratio": 0.667}
    assert body["samples"]["count"] == 0 and body["samples"]["retention_days"] == 90
    assert body["versions"]["api"] == "1.0.0" and body["versions"]["commit"] is None


@pytest.mark.django_db
def test_status_with_no_run_yet(fake_redis) -> None:  # noqa: ANN001
    body = _client(Role.FINANCE).get(URL).json()
    assert body["last_run"] is None and body["adhoc_cache"]["hit_ratio"] is None
