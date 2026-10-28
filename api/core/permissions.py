"""Role permissions (00-domain §5, N6.1). One role per user; the matrix lives here."""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from .models import Role


def _role(request: Request) -> str | None:
    user = getattr(request, "user", None)
    return getattr(user, "role", None) if user is not None and user.is_authenticated else None


class ReadAnyWriteOps(BasePermission):
    """Every role reads; only ops writes (locations, catalogue, departures)."""

    message = "Only the ops role may change this."

    def has_permission(self, request: Request, view) -> bool:  # noqa: ANN001
        role = _role(request)
        if role is None:
            return False
        return request.method in SAFE_METHODS or role == Role.OPS


class IsOps(BasePermission):
    message = "Only the ops role may do this."

    def has_permission(self, request: Request, view) -> bool:  # noqa: ANN001
        return _role(request) == Role.OPS
