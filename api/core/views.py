"""Health endpoints (docs/06-operations.md §9, 02-architecture.md §7.2).

healthz: liveness, the process answers; no dependency is touched.
readyz: readiness, the dependencies the API needs are reachable; 503 names the missing one.
Both are unauthenticated and live at the root, not under /api/v1.
"""

from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthzView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    schema = None  # probes are not part of the public API contract

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadyzView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    schema = None

    def get(self, request: Request) -> Response:
        checks = {"database": _database_ok(), "redis": _redis_ok()}
        ready = all(checks.values())
        return Response(
            {"status": "ok" if ready else "unavailable", "checks": checks},
            status=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _redis_ok() -> bool:
    try:
        from core.redis_client import redis_connection

        return bool(redis_connection().ping())
    except Exception:  # noqa: BLE001
        return False


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except Exception:  # noqa: BLE001  any database error means "not ready", never a 500
        return False
