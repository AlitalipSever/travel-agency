"""L3.2 to L3.6 and L4.1 to L4.5 over HTTP."""

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core import settings_store
from core.models import Role, User
from locations.models import Location
from weather import samples
from weather.models import SampleKind, WeatherSample
from weather.upstream import gateway
from weather.upstream.fixtures import MockWeatherClient

URL = "/api/v1/locations/brackets"
EDGES = "/api/v1/locations/bracket-edges"


def _client(role: str) -> APIClient:
    user = User.objects.create_user(username=f"u-{role}", password="x", role=role)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")
    return c


@pytest.fixture
def sales(db) -> APIClient:  # noqa: ANN001
    return _client(Role.SALES)


@pytest.fixture
def ops(db) -> APIClient:  # noqa: ANN001
    return _client(Role.OPS)


def _loc(
    name: str, temp: float, age: timedelta = timedelta(minutes=5), observed: bool = True
) -> Location:
    loc = Location.objects.create(
        name=name,
        country_code="PE",
        latitude=-12.0,
        longitude=-77.0 + len(name) / 10,
        timezone="America/Lima",
    )
    if observed:
        obs = MockWeatherClient().fetch_current(-12.0, -77.0)
        import dataclasses

        obs = dataclasses.replace(obs, temp=temp, observed_at=datetime.now(tz=UTC) - age)
        samples.store_observation(loc, obs)
    return loc


@pytest.mark.django_db
def test_every_location_in_exactly_one_bracket_no_data_and_counts(
    sales: APIClient, monkeypatch
) -> None:  # noqa: ANN001
    _loc("Cold", 7.8)
    _loc("Mild", 10.0)
    _loc("Warm", 24.9)
    _loc("Hot", 31.5)
    _loc("Fresh", 0.0, observed=False)
    monkeypatch.setattr(
        gateway,
        "fetch_current",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("upstream called")),
    )
    r = sales.get(URL)
    assert r.status_code == 200
    body = r.json()
    assert (
        body["mode"] == "fixed"
        and body["edges"] == [10.0, 20.0, 25.0, 30.0]
        and body["effective_buckets"] == 5
    )
    labels = [b["label"] for b in body["brackets"]]
    assert labels == ["below 10", "10 to 20", "20 to 25", "25 to 30", "30 and above"]
    assert [b["count"] for b in body["brackets"]] == [1, 1, 1, 0, 1]  # empty bracket kept (L3.4)
    placed = [row["name"] for b in body["brackets"] for row in b["locations"]]
    assert sorted(placed) == ["Cold", "Hot", "Mild", "Warm"]
    assert body["no_data"] == [
        {"id": body["no_data"][0]["id"], "name": "Fresh", "reason": "not refreshed yet"}
    ]
    assert all(
        "observed_at" in row and row["stale"] is False
        for b in body["brackets"]
        for row in b["locations"]
    )


@pytest.mark.django_db
def test_stale_mark_past_two_intervals(sales: APIClient, settings) -> None:  # noqa: ANN001
    settings.REFRESH_INTERVAL_S = 900
    _loc("Old", 15.0, age=timedelta(minutes=45))
    body = sales.get(URL).json()
    loc = body["brackets"][1]["locations"][0]
    assert loc["name"] == "Old" and loc["stale"] is True


@pytest.mark.django_db
def test_quantile_mode_shrinks_and_reports(sales: APIClient) -> None:
    for name, t in [("A", 10), ("B", 10), ("C", 20)]:
        _loc(name, t)
    body = sales.get(URL, {"mode": "quantile", "buckets": "4"}).json()
    assert body["requested_buckets"] == 4 and body["effective_buckets"] == 2
    assert body["edges"] == [20.0]
    assert [b["count"] for b in body["brackets"]] == [2, 1]  # none empty
    assert sales.get(URL, {"mode": "nope"}).status_code == 400
    assert sales.get(URL, {"mode": "quantile", "buckets": "1"}).status_code == 400


@pytest.mark.django_db
def test_quantile_mode_never_leaves_a_bracket_empty_with_real_decimals(sales: APIClient) -> None:
    for name, t in [
        ("Bogota", 18.23),
        ("BA", 18.49),
        ("Lima", 26.26),
        ("Asuncion", 27.8),
        ("Brasilia", 28.56),
    ]:
        _loc(name, t)
    body = sales.get(URL, {"mode": "quantile", "buckets": "4"}).json()
    assert body["effective_buckets"] == 4
    assert all(b["count"] >= 1 for b in body["brackets"]), [b["count"] for b in body["brackets"]]


@pytest.mark.django_db
def test_edges_setting_applies_on_the_next_read_and_is_ops_only(
    sales: APIClient, ops: APIClient
) -> None:
    _loc("Mild", 12.0)
    assert sales.get(EDGES).json() == {"edges": [10.0, 20.0, 25.0, 30.0]}
    assert sales.put(EDGES, {"edges": [5, 15]}, format="json").status_code == 403
    assert ops.put(EDGES, {"edges": [5, 15]}, format="json").status_code == 200
    body = sales.get(URL).json()
    assert body["edges"] == [5.0, 15.0]
    assert [b["label"] for b in body["brackets"]] == ["below 5", "5 to 15", "15 and above"]
    assert settings_store.bracket_edges() == [5.0, 15.0]
    bad = ops.put(EDGES, {"edges": [20, 10]}, format="json")
    assert bad.status_code == 400 and bad.json()["type"] == "/problems/validation"
    assert ops.put(EDGES, {"edges": list(range(11))}, format="json").status_code == 400


@pytest.mark.django_db
def test_one_query_for_all_observations(sales: APIClient, django_assert_max_num_queries) -> None:  # noqa: ANN001
    for i in range(6):
        _loc(f"L{i}", 10 + i)
    with django_assert_max_num_queries(8):  # auth, settings, locations, observations, last run
        assert sales.get(URL).status_code == 200
    assert WeatherSample.objects.filter(kind=SampleKind.OBSERVATION).count() == 6
