"""N3.2: liveness and readiness probes."""

import pytest
from rest_framework.test import APIClient


def test_healthz_answers_without_dependencies() -> None:
    client = APIClient()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readyz_is_ok_when_the_database_answers() -> None:
    client = APIClient()
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] is True


def test_readyz_reports_503_when_the_database_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    from core import views

    monkeypatch.setattr(views, "_database_ok", lambda: False)
    response = APIClient().get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "checks": {"database": False}}
