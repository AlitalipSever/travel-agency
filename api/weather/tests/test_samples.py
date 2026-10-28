"""ADR 0012: samples are upserted (newest wins), observations and forecasts coexist, retention."""

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from locations.models import Location
from weather import samples
from weather.models import RefreshRun, RefreshTrigger, SampleKind, WeatherSample
from weather.upstream.fixtures import MockWeatherClient


@pytest.fixture
def lima(db) -> Location:  # noqa: ANN001
    return Location.objects.create(
        name="Lima", country_code="PE", latitude=-12.046, longitude=-77.043, timezone="America/Lima"
    )


@pytest.mark.django_db
def test_store_forecast_upserts_newest_wins(lima: Location) -> None:
    client = MockWeatherClient()
    first = client.fetch_forecast(-12.046, -77.043)
    assert samples.store_forecast(lima, first) == 40
    assert WeatherSample.objects.count() == 40

    # Second fetch, same slots, one temperature changed: still 40 rows, value updated.
    slot = first.slots[3]
    changed = (
        type(slot)(**{**slot.__dict__, "temp": slot.temp + 10})
        if hasattr(slot, "__dict__")
        else None
    )
    if changed is None:  # slots dataclass: rebuild through replace
        import dataclasses

        changed = dataclasses.replace(slot, temp=slot.temp + 10)
    second = dataclasses_replace_forecast(first, 3, changed)
    samples.store_forecast(lima, second)
    assert WeatherSample.objects.count() == 40
    row = WeatherSample.objects.get(
        location=lima, slot_time=slot.slot_time, kind=SampleKind.FORECAST
    )
    assert float(row.temp) == pytest.approx(round(slot.temp + 10, 2))


def dataclasses_replace_forecast(forecast, index, new_slot):  # noqa: ANN001, ANN201
    import dataclasses

    slots = list(forecast.slots)
    slots[index] = new_slot
    return dataclasses.replace(forecast, slots=tuple(slots), fetched_at=datetime.now(tz=UTC))


@pytest.mark.django_db
def test_observation_and_forecast_coexist_for_the_same_time(lima: Location) -> None:
    client = MockWeatherClient()
    fc = client.fetch_forecast(-12.046, -77.043)
    samples.store_forecast(lima, fc)
    obs = client.fetch_current(-12.046, -77.043)
    # Force the observation onto the first slot's instant to prove both kinds can exist.
    obs = dataclasses.replace(obs, observed_at=fc.slots[0].slot_time)
    samples.store_observation(lima, obs)
    samples.store_observation(lima, obs)  # idempotent
    assert WeatherSample.objects.filter(slot_time=fc.slots[0].slot_time).count() == 2
    latest = samples.latest_observation(lima)
    assert latest is not None and latest.kind == SampleKind.OBSERVATION


@pytest.mark.django_db
def test_samples_between_is_half_open_and_ordered(lima: Location) -> None:
    fc = MockWeatherClient().fetch_forecast(-12.046, -77.043)
    samples.store_forecast(lima, fc)
    start, end = fc.slots[0].slot_time, fc.slots[8].slot_time
    rows = list(samples.samples_between(lima, start, end))
    assert len(rows) == 8
    assert rows[0].slot_time == start and rows[-1].slot_time < end


@pytest.mark.django_db
def test_prune_removes_only_old_rows_and_runs(lima: Location) -> None:
    fc = MockWeatherClient().fetch_forecast(-12.046, -77.043)
    samples.store_forecast(lima, fc)
    old = WeatherSample.objects.order_by("slot_time").first()
    assert old is not None
    old.slot_time = datetime.now(tz=UTC) - timedelta(days=100)
    old.save()
    run = samples.start_run(RefreshTrigger.MANUAL, locations=1)
    RefreshRun.objects.filter(pk=run.pk).update(
        started_at=datetime.now(tz=UTC) - timedelta(days=100)
    )
    assert samples.prune(90) == 2
    assert WeatherSample.objects.count() == 39 and RefreshRun.objects.count() == 0


@pytest.mark.django_db
def test_run_lifecycle() -> None:
    run = samples.start_run(RefreshTrigger.SCHEDULED, locations=13)
    assert run.finished_at is None
    samples.finish_run(run, calls_used=26, failures=1, effective_interval_s=900, notes="ok")
    again = samples.last_run()
    assert again is not None and again.calls_used == 26 and again.finished_at is not None
