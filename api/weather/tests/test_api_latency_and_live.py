"""W1.1, W1.2 and W4.7 as timed checks, and the one live smoke test (skipped without a key).

Timing tests are generous on purpose: they catch a path that accidentally calls the upstream
or runs a slow query, not CI jitter.
"""

import os
import time

import httpx
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Role, User
from locations.models import Location
from weather import samples
from weather.upstream import gateway
from weather.upstream.client import HttpWeatherClient, UpstreamError
from weather.upstream.fixtures import MockWeatherClient

URL = "/api/v1/weather/current"


@pytest.fixture
def client(db) -> APIClient:  # noqa: ANN001
    user = User.objects.create_user(username="t1", password="x", role=Role.SALES)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")
    return c


def _p95_ms(fn, runs: int = 20) -> float:  # noqa: ANN001
    durations = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        durations.append((time.perf_counter() - t0) * 1000)
    durations.sort()
    return durations[int(0.95 * (runs - 1))]


@pytest.mark.django_db
def test_w1_1_known_location_answers_from_stored_data_fast(client: APIClient) -> None:
    lima = Location.objects.create(
        name="Lima", country_code="PE", latitude=-12.046, longitude=-77.043, timezone="America/Lima"
    )
    samples.store_observation(lima, MockWeatherClient().fetch_current(-12.046, -77.043))
    p95 = _p95_ms(lambda: client.get(URL, {"lat": -12.046, "lon": -77.043}))
    assert p95 < 100, f"p95 {p95:.1f} ms"


@pytest.mark.django_db
def test_w1_1_cached_ad_hoc_coordinate_answers_fast(client: APIClient) -> None:
    client.get(URL, {"lat": -33.45, "lon": -70.66})  # warms the cache (mock upstream)
    p95 = _p95_ms(lambda: client.get(URL, {"lat": -33.45, "lon": -70.66}))
    assert p95 < 100, f"p95 {p95:.1f} ms"


@pytest.mark.django_db
def test_w1_2_first_time_coordinate_stays_under_1500ms_including_upstream(
    client: APIClient, monkeypatch
) -> None:  # noqa: ANN001
    real = gateway.fetch_current

    def slow_upstream(lat: float, lon: float, share: str = "adhoc"):  # noqa: ANN202
        time.sleep(0.3)  # a slow but answering upstream
        return real(lat, lon, share)  # type: ignore[arg-type]

    monkeypatch.setattr(gateway, "fetch_current", slow_upstream)
    t0 = time.perf_counter()
    r = client.get(URL, {"lat": 10.123, "lon": 20.456})
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200 and r.json()["source"] == "live"
    assert elapsed_ms < 1500, f"{elapsed_ms:.0f} ms"


def test_w4_7_a_hanging_upstream_is_cut_at_the_configured_timeout() -> None:
    """The client gives up after timeout_s; the caller is never held longer than that."""

    def hang(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("no answer", request=request)

    client = HttpWeatherClient(api_key="k", base_url="https://owm.test", timeout_s=0.2)
    client._client = httpx.Client(base_url="https://owm.test", transport=httpx.MockTransport(hang))
    t0 = time.perf_counter()
    with pytest.raises(UpstreamError):
        client.fetch_current(1.0, 2.0)
    assert (time.perf_counter() - t0) < 0.5
    # and the real client carries the configured deadline
    real = HttpWeatherClient(api_key="k", base_url="https://owm.test", timeout_s=5.0)
    assert real._client.timeout.read == 5.0 and real._client.timeout.connect == 3.0


@pytest.mark.skipif(
    not os.environ.get("OPENWEATHER_API_KEY"), reason="live check needs OPENWEATHER_API_KEY"
)
def test_live_smoke_against_openweathermap() -> None:
    """One real call when a key is present (05 B2 done-when); never runs in CI without a key."""
    from django.conf import settings

    client = HttpWeatherClient(
        api_key=os.environ["OPENWEATHER_API_KEY"],
        base_url=settings.OPENWEATHER_BASE_URL,
        timeout_s=10.0,
    )
    obs = client.fetch_current(-12.046, -77.043)
    assert -20 < obs.temp < 45 and obs.timezone_offset_s == -18000
    fc = client.fetch_forecast(-12.046, -77.043)
    assert len(fc.slots) == 40
