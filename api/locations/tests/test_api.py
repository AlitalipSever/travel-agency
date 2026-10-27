"""L1.1, L1.3, L1.4, L1.5 and the role matrix (N6.1) over HTTP."""

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Partner, Role, User
from locations.models import Location
from weather.models import RefreshRun, WeatherSample

URL = "/api/v1/locations"


def _client(role: str, partner: Partner | None = None) -> APIClient:
    user = User.objects.create_user(username=f"u-{role}", password="x", role=role, partner=partner)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")
    return c


@pytest.fixture
def ops(db) -> APIClient:  # noqa: ANN001
    return _client(Role.OPS)


@pytest.fixture
def sales(db) -> APIClient:  # noqa: ANN001
    return _client(Role.SALES)


@pytest.mark.django_db(transaction=True)
def test_ops_creates_zone_is_derived_and_weather_arrives_at_once(ops: APIClient) -> None:
    r = ops.post(
        URL,
        {"name": "Cusco", "country_code": "pe", "latitude": -13.5319, "longitude": -71.9675},
        format="json",
    )
    assert r.status_code == 201, r.content
    body = r.json()
    assert (
        body["timezone"] == "America/Lima"
        and body["country_code"] == "PE"
        and body["active"] is True
    )
    # L1.5: the on-create refresh ran (eager Celery in tests) and stored samples
    run = RefreshRun.objects.first()
    assert run is not None and run.trigger == "on_create", "no on_create run recorded"
    assert run.failures == 0, f"on_create refresh failed: {run.notes}"
    assert WeatherSample.objects.filter(location_id=body["id"]).count() == 41


@pytest.mark.django_db
def test_every_role_reads_only_ops_writes(ops: APIClient, sales: APIClient) -> None:
    ops.post(
        URL,
        {"name": "Lima", "country_code": "PE", "latitude": -12.046, "longitude": -77.043},
        format="json",
    )
    assert sales.get(URL).status_code == 200
    r = sales.post(
        URL,
        {"name": "Cusco", "country_code": "PE", "latitude": -13.53, "longitude": -71.97},
        format="json",
    )
    assert r.status_code == 403 and r.json()["type"] == "/problems/forbidden"
    finance = _client(Role.FINANCE)
    partner = _client(Role.PARTNER, Partner.objects.create(name="P1"))
    assert finance.get(URL).status_code == 200 and partner.get(URL).status_code == 200
    assert APIClient().get(URL).status_code == 401


@pytest.mark.django_db
def test_validation_unique_and_unknown_zone(ops: APIClient) -> None:
    ok = ops.post(
        URL,
        {"name": "Lima", "country_code": "PE", "latitude": -12.046, "longitude": -77.043},
        format="json",
    )
    assert ok.status_code == 201
    dup = ops.post(
        URL,
        {"name": "Lima", "country_code": "PE", "latitude": -12.0, "longitude": -77.0},
        format="json",
    )
    assert dup.status_code == 400 and dup.json()["type"] == "/problems/validation"
    bad = ops.post(
        URL, {"name": "X", "country_code": "PE", "latitude": 95, "longitude": 0}, format="json"
    )
    assert bad.status_code == 400
    zone = ops.post(
        URL,
        {
            "name": "Y",
            "country_code": "PE",
            "latitude": -12.0,
            "longitude": -77.0,
            "timezone": "Mars/Olympus",
        },
        format="json",
    )
    assert zone.status_code == 400 and zone.json()["errors"][0]["field"] == "timezone"


@pytest.mark.django_db
def test_deactivate_filters_and_soft_delete(ops: APIClient, sales: APIClient) -> None:
    created = ops.post(
        URL,
        {"name": "Lima", "country_code": "PE", "latitude": -12.046, "longitude": -77.043},
        format="json",
    ).json()
    pk = created["id"]
    assert len(sales.get(URL).json()["results"]) == 1
    assert ops.patch(f"{URL}/{pk}", {"active": False}, format="json").status_code == 200
    assert sales.get(URL).json()["results"] == []  # default list is active only (L1.3)
    assert len(sales.get(URL, {"active": "false"}).json()["results"]) == 1
    assert ops.delete(f"{URL}/{pk}").status_code == 204
    assert sales.get(f"{URL}/{pk}").status_code == 404
    assert Location.objects.filter(pk=pk).exists()  # kept (L1.4)


@pytest.mark.django_db(transaction=True)
def test_weather_by_location_id(ops: APIClient, sales: APIClient) -> None:
    created = ops.post(
        URL,
        {"name": "Lima", "country_code": "PE", "latitude": -12.046, "longitude": -77.043},
        format="json",
    ).json()
    cur = sales.get(f"{URL}/{created['id']}/weather/current")
    assert cur.status_code == 200 and cur.json()["source"] == "sample"
    fc = sales.get(f"{URL}/{created['id']}/weather/forecast")
    assert fc.status_code == 200 and fc.json()["source"] == "sample" and len(fc.json()["days"]) == 5


@pytest.mark.django_db
def test_list_filters_and_order(ops: APIClient) -> None:
    for name, cc, lat, lon in [
        ("Lima", "PE", -12.046, -77.043),
        ("Cusco", "PE", -13.53, -71.97),
        ("Quito", "EC", -0.23, -78.52),
    ]:
        ops.post(
            URL,
            {"name": name, "country_code": cc, "latitude": lat, "longitude": lon},
            format="json",
        )
    names = [x["name"] for x in ops.get(URL).json()["results"]]
    assert names == ["Cusco", "Lima", "Quito"]
    assert [x["name"] for x in ops.get(URL, {"country": "pe"}).json()["results"]] == [
        "Cusco",
        "Lima",
    ]
    assert [x["name"] for x in ops.get(URL, {"q": "qui"}).json()["results"]] == ["Quito"]
