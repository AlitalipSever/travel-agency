"""W4.2 spacing, W4.4 partial failure, the run lock and the on-create refresh."""

from datetime import UTC, datetime, timedelta

import pytest

from locations.models import Location
from weather import tasks
from weather.models import RefreshRun, WeatherSample
from weather.upstream import breaker, gateway
from weather.upstream.budget import Share
from weather.upstream.client import UpstreamError


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks, "_sleep", lambda s: None)


@pytest.fixture
def two_locations(db) -> list[Location]:  # noqa: ANN001
    return [
        Location.objects.create(
            name="Lima",
            country_code="PE",
            latitude=-12.046,
            longitude=-77.043,
            timezone="America/Lima",
        ),
        Location.objects.create(
            name="La Paz",
            country_code="BO",
            latitude=-16.4897,
            longitude=-68.1193,
            timezone="America/La_Paz",
        ),
    ]


def test_spacing_spreads_over_the_interval_and_respects_the_share(settings) -> None:  # noqa: ANN001
    settings.REFRESH_INTERVAL_S = 900
    settings.UPSTREAM_REFRESH_SHARE = 40
    assert tasks.spacing_seconds(13) == pytest.approx(900 / 13)  # 69 s apart, well inside the share
    # 600 locations would need 1200 calls: the share bound (3 s per location) wins and the
    # run takes 1800 s, longer than the interval: the effective interval lengthens.
    assert tasks.spacing_seconds(600) == pytest.approx(3.0)
    assert tasks.spacing_seconds(0) == 0.0


@pytest.mark.django_db
def test_refresh_all_stores_samples_and_a_run(two_locations: list[Location]) -> None:
    result = tasks.refresh_all(trigger="manual")
    assert result == {"locations": 2, "calls": 4, "failures": 0}
    assert WeatherSample.objects.count() == 2 * 41  # 40 forecast slots + 1 observation each
    run = RefreshRun.objects.get()
    assert run.finished_at is not None and run.calls_used == 4 and run.trigger == "manual"


@pytest.mark.django_db
def test_one_failing_location_does_not_stop_the_run(
    two_locations: list[Location], monkeypatch
) -> None:  # noqa: ANN001
    real = gateway.fetch_current

    def flaky(lat: float, lon: float, share: Share = "adhoc"):  # noqa: ANN202
        if lat < -15:  # La Paz
            raise UpstreamError("boom")
        return real(lat, lon, share)

    monkeypatch.setattr(gateway, "fetch_current", flaky)
    result = tasks.refresh_all(trigger="manual")
    assert result["failures"] == 1 and result["calls"] == 2
    assert WeatherSample.objects.filter(location__name="Lima").count() == 41
    assert WeatherSample.objects.filter(location__name="La Paz").count() == 0
    assert "La Paz" in RefreshRun.objects.get().notes


@pytest.mark.django_db
def test_run_is_skipped_while_the_lock_is_held(two_locations: list[Location], fake_redis) -> None:  # noqa: ANN001
    fake_redis.set(tasks.LOCK_KEY, "1")
    assert tasks.refresh_all() == {"skipped": 1}
    assert RefreshRun.objects.count() == 0


@pytest.mark.django_db
def test_breaker_open_counts_as_failure_without_calls(
    two_locations: list[Location], settings
) -> None:  # noqa: ANN001
    settings.BREAKER_FAILURES = 1
    breaker.record_failure()
    result = tasks.refresh_all()
    assert result == {"locations": 2, "calls": 0, "failures": 2}


@pytest.mark.django_db
def test_refresh_one_now(two_locations: list[Location]) -> None:
    lima = two_locations[0]
    assert tasks.refresh_one_now(str(lima.pk)) == {"calls": 2}
    assert WeatherSample.objects.filter(location=lima).count() == 41
    assert RefreshRun.objects.get().trigger == "on_create"


@pytest.mark.django_db
def test_prune_uses_the_retention_setting(two_locations: list[Location]) -> None:
    tasks.refresh_all(trigger="manual")
    old = WeatherSample.objects.order_by("slot_time").first()
    assert old is not None
    old.slot_time = datetime.now(tz=UTC) - timedelta(days=200)
    old.save()
    assert tasks.prune_samples() == 1
