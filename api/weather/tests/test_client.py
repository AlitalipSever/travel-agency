"""W1/W2 groundwork: the adapter maps upstream JSON to our types and upstream failures to our
errors; the mock client serves fixtures shifted to now."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from weather import fixtures
from weather.client import (
    HttpWeatherClient,
    UpstreamError,
    UpstreamRateLimited,
    UpstreamRejected,
    get_client,
    parse_current,
    parse_forecast,
)
from weather.fixtures import MockWeatherClient


def test_parse_current_maps_fields() -> None:
    obs = parse_current(fixtures.load("current", "lima"), -12.046, -77.043)
    assert obs.temp == pytest.approx(19.4)
    assert obs.condition_code == 803
    assert obs.timezone_offset_s == -18000
    assert obs.observed_at.tzinfo is not None
    assert obs.is_day is True


def test_parse_forecast_gives_40_utc_slots_with_day_flag_and_pop() -> None:
    fc = parse_forecast(fixtures.load("forecast", "lima"), -12.046, -77.043)
    assert len(fc.slots) == 40
    assert all(s.slot_time.tzinfo is UTC for s in fc.slots)
    gaps = {fc.slots[i + 1].slot_time - fc.slots[i].slot_time for i in range(39)}
    assert gaps == {timedelta(hours=3)}
    assert any(s.pop and s.pop > 0 for s in fc.slots)
    assert {s.is_day for s in fc.slots} == {True, False}


def test_mock_client_picks_nearest_place_and_shifts_to_now() -> None:
    client = MockWeatherClient()
    assert fixtures.nearest_slug(-16.5, -68.1) == "la_paz"
    fc = client.fetch_forecast(-16.5, -68.1)
    now = datetime.now(tz=UTC)
    assert now < fc.slots[0].slot_time <= now + timedelta(hours=3)
    assert fc.slots[0].slot_time.hour % 3 == 0
    obs = client.fetch_current(-12.0, -77.0)
    assert abs((obs.observed_at - now).total_seconds()) < 5


def test_get_client_is_the_mock_without_a_key(settings) -> None:  # noqa: ANN001
    settings.OPENWEATHER_API_KEY = ""
    assert isinstance(get_client(), MockWeatherClient)


def _client_with(handler) -> HttpWeatherClient:  # noqa: ANN001
    client = HttpWeatherClient(api_key="k", base_url="https://owm.test", timeout_s=1.0)
    client._client = httpx.Client(
        base_url="https://owm.test", transport=httpx.MockTransport(handler)
    )
    return client


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (429, UpstreamRateLimited),
        (401, UpstreamRejected),
        (404, UpstreamRejected),
        (500, UpstreamError),
        (503, UpstreamError),
    ],
)
def test_http_statuses_map_to_our_errors(status: int, error: type[Exception]) -> None:
    client = _client_with(lambda req: httpx.Response(status, json={"cod": status}))
    with pytest.raises(error):
        client.fetch_current(1.0, 2.0)


def test_timeout_and_bad_body_are_upstream_errors() -> None:
    def timeout(req):  # noqa: ANN001, ANN202
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(UpstreamError):
        _client_with(timeout).fetch_current(1.0, 2.0)
    with pytest.raises(UpstreamError):
        _client_with(lambda req: httpx.Response(200, text="not json")).fetch_current(1.0, 2.0)


def test_real_client_sends_metric_units_and_coordinates() -> None:
    seen = {}

    def handler(req):  # noqa: ANN001, ANN202
        seen.update(dict(req.url.params))
        return httpx.Response(200, json=fixtures.load("current", "lima"))

    _client_with(handler).fetch_current(-12.046, -77.043)
    assert seen["units"] == "metric" and seen["lat"] == "-12.046" and seen["appid"] == "k"
