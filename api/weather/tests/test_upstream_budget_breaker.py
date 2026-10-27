"""W4.2, W4.3, W4.6: budget shares, the breaker's three states, and the gateway's order."""

from datetime import UTC, datetime

import pytest

from weather.upstream import breaker, budget, gateway
from weather.upstream.client import UpstreamError, UpstreamRejected


def test_budget_grants_up_to_the_share_then_refuses(settings) -> None:  # noqa: ANN001
    settings.UPSTREAM_ADHOC_SHARE = 3
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    assert [budget.acquire("adhoc", now) for _ in range(4)] == [True, True, True, False]
    assert budget.used("adhoc", now) == 3
    assert budget.used_this_month(now) == 3  # refused calls are not counted


def test_shares_are_independent_bulkheads(settings) -> None:  # noqa: ANN001
    settings.UPSTREAM_ADHOC_SHARE = 1
    settings.UPSTREAM_REFRESH_SHARE = 2
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    assert budget.acquire("adhoc", now) and not budget.acquire("adhoc", now)
    assert budget.acquire("refresh", now) and budget.acquire("refresh", now)


def test_budget_resets_every_minute(settings) -> None:  # noqa: ANN001
    settings.UPSTREAM_ADHOC_SHARE = 1
    t0 = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    t1 = datetime(2026, 3, 10, 12, 1, tzinfo=UTC)
    assert budget.acquire("adhoc", t0) and not budget.acquire("adhoc", t0)
    assert budget.acquire("adhoc", t1)


def test_breaker_opens_after_threshold_and_probes_after_cooldown(settings, fake_redis) -> None:  # noqa: ANN001
    settings.BREAKER_FAILURES = 2
    settings.BREAKER_COOLDOWN_S = 60
    assert breaker.state() == "closed" and breaker.allow()
    breaker.record_failure()
    assert breaker.allow()
    breaker.record_failure()
    assert breaker.state() == "open" and not breaker.allow()
    fake_redis.delete(breaker.OPEN_KEY)  # cooldown elapsed
    assert breaker.allow()  # the single probe
    assert breaker.state() == "half_open"
    assert not breaker.allow()  # a second caller waits
    breaker.record_success()
    assert breaker.state() == "closed" and breaker.allow()


def test_gateway_retries_transient_errors_then_raises(settings, monkeypatch) -> None:  # noqa: ANN001
    settings.UPSTREAM_RETRIES = 2
    settings.UPSTREAM_ADHOC_SHARE = 10
    monkeypatch.setattr(gateway.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def failing() -> None:
        calls["n"] += 1
        raise UpstreamError("boom")

    with pytest.raises(UpstreamError):
        gateway._guarded(failing, "adhoc")
    assert calls["n"] == 3  # 1 + 2 retries
    assert budget.used("adhoc") == 3  # every attempt costs a call
    assert breaker.snapshot()["consecutive_failures"] == 3


def test_gateway_does_not_retry_rejections() -> None:
    calls = {"n": 0}

    def rejected() -> None:
        calls["n"] += 1
        raise UpstreamRejected("401")

    with pytest.raises(UpstreamRejected):
        gateway._guarded(rejected, "adhoc")
    assert calls["n"] == 1
    assert breaker.snapshot()["consecutive_failures"] == 0


def test_gateway_fails_fast_when_breaker_open(settings) -> None:  # noqa: ANN001
    settings.BREAKER_FAILURES = 1
    breaker.record_failure()
    with pytest.raises(breaker.BreakerOpen):
        gateway._guarded(lambda: 1, "adhoc")
    assert budget.used("adhoc") == 0  # no call was charged


def test_gateway_raises_budget_exhausted(settings) -> None:  # noqa: ANN001
    settings.UPSTREAM_ADHOC_SHARE = 0
    with pytest.raises(gateway.BudgetExhausted):
        gateway._guarded(lambda: 1, "adhoc")


def test_gateway_fetches_through_the_mock_client(settings) -> None:  # noqa: ANN001
    settings.OPENWEATHER_API_KEY = ""
    obs = gateway.fetch_current(-12.046, -77.043)
    assert obs.temp == pytest.approx(19.4)
    assert budget.used("adhoc") == 1
    assert breaker.state() == "closed"
