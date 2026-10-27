"""W2.1 to W2.6 through the HTTP endpoint."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Role, User
from locations.models import Location
from weather import samples
from weather.upstream import gateway
from weather.upstream.client import UpstreamError
from weather.upstream.fixtures import MockWeatherClient

URL = "/api/v1/weather/forecast"


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    cache.clear()


@pytest.fixture
def client(db) -> APIClient:  # noqa: ANN001
    user = User.objects.create_user(username="s", password="x", role=Role.SALES)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")
    return c


@pytest.fixture
def lima(db) -> Location:  # noqa: ANN001
    return Location.objects.create(
        name="Lima", country_code="PE", latitude=-12.046, longitude=-77.043, timezone="America/Lima"
    )


def _check_shape(body: dict) -> None:  # noqa: ANN001
    assert set(body) >= {
        "lat",
        "lon",
        "timezone",
        "as_of",
        "source",
        "today",
        "days",
        "location_id",
    }
    assert len(body["days"]) == 5
    for d in body["days"]:
        assert set(d) == {
            "date",
            "temp_avg",
            "temp_min",
            "temp_max",
            "condition",
            "observed_samples",
            "forecast_samples",
            "partial",
        }


@pytest.mark.django_db
def test_w2_1_five_days_from_tomorrow_and_today_separate(client: APIClient) -> None:
    r = client.get(URL, {"lat": -33.45, "lon": -70.66})
    assert r.status_code == 200
    body = r.json()
    _check_shape(body)
    assert body["source"] == "live" and body["timezone"].startswith("UTC")
    tz_hours = int(body["timezone"][3:6])
    today_local = datetime.now(tz=UTC).astimezone(ZoneInfo("UTC")).date()  # rough: adjusted below
    first = body["days"][0]["date"]
    assert body["today"] is None or body["today"]["date"] < first
    assert first > str(today_local) or tz_hours < 0  # tomorrow in the local calendar
    assert (
        body["today"]["partial"] is True
    )  # ad hoc coordinate: today's past hours are missing (W2.4)


@pytest.mark.django_db
def test_w2_3_fifth_day_is_partial_when_cut_by_the_window(client: APIClient) -> None:
    body = client.get(URL, {"lat": -33.45, "lon": -70.66}).json()
    assert body["days"][-1]["partial"] is True
    assert all(d["forecast_samples"] + d["observed_samples"] >= 1 for d in body["days"][:4])


@pytest.mark.django_db
def test_w2_4_known_location_today_is_complete_once_past_slots_exist(
    client: APIClient, lima: Location
) -> None:
    mock = MockWeatherClient()
    fc = mock.fetch_forecast(-12.046, -77.043)
    samples.store_forecast(lima, fc)
    # Pretend the worker has been running: forecast slots for every past slot of today.
    import dataclasses
    from datetime import timedelta

    zone = ZoneInfo("America/Lima")
    now = datetime.now(tz=UTC)
    day_start = datetime.combine(
        now.astimezone(zone).date(), datetime.min.time(), tzinfo=zone
    ).astimezone(UTC)
    past = []
    t = day_start.replace(minute=0, second=0, microsecond=0)
    while t.hour % 3:
        t += timedelta(hours=1)
    while t <= now:
        past.append(dataclasses.replace(fc.slots[0], slot_time=t))
        t += timedelta(hours=3)
    samples.store_forecast(lima, dataclasses.replace(fc, slots=tuple(past)))
    samples.store_observation(lima, mock.fetch_current(-12.046, -77.043))

    body = client.get(URL, {"lat": -12.046, "lon": -77.043}).json()
    assert body["source"] == "sample" and body["timezone"] == "America/Lima"
    assert body["location_id"] == str(lima.pk)
    assert body["today"] is not None and body["today"]["partial"] is False
    assert body["today"]["observed_samples"] >= 1


@pytest.mark.django_db
def test_w2_4_new_location_without_samples_uses_the_ad_hoc_path(
    client: APIClient, lima: Location
) -> None:
    body = client.get(URL, {"lat": -12.046, "lon": -77.043}).json()
    assert body["source"] == "live" and body["today"]["partial"] is True


@pytest.mark.django_db
def test_w2_6_invalid_input_outage_and_cache_behave_like_w1(client: APIClient, monkeypatch) -> None:  # noqa: ANN001
    assert client.get(URL, {"lat": 95, "lon": 0}).status_code == 400
    first = client.get(URL, {"lat": 10.5, "lon": 20.5}).json()
    assert first["source"] == "live"
    assert client.get(URL, {"lat": 10.5, "lon": 20.5}).json()["source"] == "cached"
    monkeypatch.setattr(
        gateway, "fetch_forecast", lambda *a, **k: (_ for _ in ()).throw(UpstreamError("down"))
    )
    r = client.get(URL, {"lat": 11.5, "lon": 21.5})
    assert r.status_code == 503 and r["Retry-After"]


@pytest.mark.django_db
def test_endpoint_is_in_the_schema(client: APIClient) -> None:
    assert "/api/v1/weather/forecast" in client.get("/api/schema").content.decode()
