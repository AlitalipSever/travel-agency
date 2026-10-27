"""W1.1 to W1.5 through the HTTP endpoint, plus the per-token throttle (W4.3)."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Role, User
from locations.models import Location
from weather import adhoc, samples
from weather.upstream import gateway
from weather.upstream.client import UpstreamError
from weather.upstream.fixtures import MockWeatherClient

URL = "/api/v1/weather/current"


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    cache.clear()


@pytest.fixture
def client(db) -> APIClient:  # noqa: ANN001
    user = User.objects.create_user(username="sales1", password="x", role=Role.SALES)
    token = Token.objects.create(user=user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return c


@pytest.fixture
def lima(db) -> Location:  # noqa: ANN001
    return Location.objects.create(
        name="Lima", country_code="PE", latitude=-12.046, longitude=-77.043, timezone="America/Lima"
    )


def test_requires_a_token() -> None:
    r = APIClient().get(URL, {"lat": 1, "lon": 2})
    assert r.status_code == 401


@pytest.mark.django_db
def test_invalid_coordinates_are_400_and_cost_no_upstream_call(
    client: APIClient, monkeypatch
) -> None:  # noqa: ANN001
    called = {"n": 0}
    monkeypatch.setattr(gateway, "fetch_current", lambda *a, **k: called.__setitem__("n", 1))
    bad: list[dict[str, Any]] = [
        {"lat": 95, "lon": 0},
        {"lat": 0},
        {"lat": "x", "lon": 0},
        {"lat": 0, "lon": 0, "units": "f"},
    ]
    for params in bad:
        r = client.get(URL, params)
        assert r.status_code == 400, params
        assert r["Content-Type"].startswith("application/problem+json")
    assert called["n"] == 0


@pytest.mark.django_db
def test_known_location_is_served_from_samples(
    client: APIClient, lima: Location, monkeypatch
) -> None:  # noqa: ANN001
    obs = MockWeatherClient().fetch_current(-12.046, -77.043)
    samples.store_observation(lima, obs)
    monkeypatch.setattr(
        gateway,
        "fetch_current",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("upstream called")),
    )
    r = client.get(URL, {"lat": -12.0462, "lon": -77.0431})  # 25 m away
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "sample" and body["timezone"] == "America/Lima"
    assert body["location_id"] == str(lima.pk)
    assert body["temp"] == pytest.approx(obs.temp, abs=0.01)


@pytest.mark.django_db
def test_ad_hoc_is_live_then_cached(client: APIClient) -> None:
    first = client.get(URL, {"lat": -33.45, "lon": -70.66})
    assert first.status_code == 200 and first.json()["source"] == "live"
    second = client.get(URL, {"lat": -33.4504, "lon": -70.6596})  # same 3-decimal key
    assert second.status_code == 200 and second.json()["source"] == "cached"
    assert second.json()["timezone"].startswith("UTC")


@pytest.mark.django_db
def test_outage_with_a_stored_value_is_stale(client: APIClient, monkeypatch) -> None:  # noqa: ANN001
    client.get(URL, {"lat": -33.45, "lon": -70.66})
    # Age the cached value past freshness, then break the upstream.
    conn = adhoc.redis_connection()
    key = "owm:current:-33.450,-70.660"
    data = json.loads(cast(str, conn.get(key)))
    data["stored_at"] = (datetime.now(tz=UTC) - timedelta(seconds=adhoc.FRESH_S + 5)).isoformat()
    conn.set(key, json.dumps(data))
    monkeypatch.setattr(
        gateway, "fetch_current", lambda *a, **k: (_ for _ in ()).throw(UpstreamError("down"))
    )
    r = client.get(URL, {"lat": -33.45, "lon": -70.66})
    assert r.status_code == 200
    assert r.json()["source"] == "stale" and r.json()["age_s"] >= adhoc.FRESH_S


@pytest.mark.django_db
def test_outage_without_a_stored_value_is_503(client: APIClient, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        gateway, "fetch_current", lambda *a, **k: (_ for _ in ()).throw(UpstreamError("down"))
    )
    r = client.get(URL, {"lat": 10.5, "lon": 20.5})
    assert r.status_code == 503
    assert r["Retry-After"] and r.json()["type"] == "/problems/upstream-unavailable"


@pytest.mark.django_db
def test_budget_exhausted_without_a_stored_value_is_429(client: APIClient, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        gateway,
        "fetch_current",
        lambda *a, **k: (_ for _ in ()).throw(gateway.BudgetExhausted("adhoc")),
    )
    r = client.get(URL, {"lat": 10.5, "lon": 20.5})
    assert r.status_code == 429 and r["Retry-After"] == "60"


@pytest.mark.django_db
def test_per_token_throttle_on_ad_hoc_only(client: APIClient, lima: Location, settings) -> None:  # noqa: ANN001
    settings.ADHOC_RATE_PER_MIN = 2
    samples.store_observation(lima, MockWeatherClient().fetch_current(-12.046, -77.043))
    assert client.get(URL, {"lat": -33.45, "lon": -70.66}).status_code == 200
    assert client.get(URL, {"lat": -33.46, "lon": -70.67}).status_code == 200
    third = client.get(URL, {"lat": -33.47, "lon": -70.68})
    assert third.status_code == 429
    assert third["X-RateLimit-Limit"] == "2" and third["Retry-After"]
    # the known location is still served: it does not count against the ad hoc limit
    assert client.get(URL, {"lat": -12.046, "lon": -77.043}).status_code == 200


@pytest.mark.django_db
def test_endpoint_is_in_the_schema(client: APIClient) -> None:
    r = client.get("/api/schema")
    assert "/api/v1/weather/current" in r.content.decode()
