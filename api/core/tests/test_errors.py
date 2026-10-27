"""04 §1 problem details: one envelope for every error, no internals (N6.4)."""

import pytest
from django.urls import path
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from core.errors import Conflict, ProblemType

# A throwaway URL map with views that raise each kind of error.


class EchoSerializer(serializers.Serializer):
    name = serializers.CharField()
    latitude = serializers.FloatField(max_value=90)


class ValidateView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):  # noqa: ANN001, ANN201
        s = EchoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(s.validated_data)


class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001, ANN201
        return Response({})


class ConflictView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):  # noqa: ANN001, ANN201
        raise Conflict("Sold out.", data={"remaining": 0}, headers={"Retry-After": "60"})


class BoomView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):  # noqa: ANN001, ANN201
        raise RuntimeError("secret internals")


urlpatterns = [
    path("t/validate", ValidateView.as_view()),
    path("t/protected", ProtectedView.as_view()),
    path("t/conflict", ConflictView.as_view()),
    path("t/boom", BoomView.as_view()),
]

handler404 = "core.errors.handler404"
handler500 = "core.errors.handler500"

pytestmark = pytest.mark.urls(__name__)


def _client() -> APIClient:
    return APIClient(raise_request_exception=False)


def test_validation_error_lists_fields() -> None:
    r = _client().post("/t/validate", {"latitude": 95}, format="json")
    assert r.status_code == 400
    assert r["Content-Type"].startswith("application/problem+json")
    body = r.json()
    assert body["type"] == ProblemType.VALIDATION
    assert body["status"] == 400 and body["instance"] == "/t/validate"
    fields = {e["field"] for e in body["errors"]}
    assert fields == {"name", "latitude"}


def test_missing_token_is_401_problem() -> None:
    r = _client().get("/t/protected")
    assert r.status_code == 401
    assert r.json()["type"] == ProblemType.UNAUTHENTICATED


def test_unknown_url_is_404_problem() -> None:
    r = _client().get("/t/nothing")
    assert r.status_code == 404
    assert r.json()["type"] == ProblemType.NOT_FOUND


def test_conflict_carries_data_and_headers() -> None:
    r = _client().post("/t/conflict")
    assert r.status_code == 409
    assert r["Retry-After"] == "60"
    body = r.json()
    assert body["type"] == ProblemType.CONFLICT
    assert body["detail"] == "Sold out." and body["remaining"] == 0


def test_unexpected_error_hides_internals() -> None:
    r = _client().get("/t/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["type"] == ProblemType.INTERNAL
    assert "secret" not in r.content.decode()
