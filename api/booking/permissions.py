"""Who may do what with bookings and travellers (00-domain §5, P6.6).

ops and sales: everything. partner: create, read and cancel its own rows (the scope is
applied in the queryset, so foreign rows are 404, never 403). finance: read only.
"""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from core.models import Role
from core.permissions import _role


class BookingPermission(BasePermission):
    message = "Your role may not do this with bookings."

    def has_permission(self, request: Request, view) -> bool:  # noqa: ANN001
        role = _role(request)
        if role is None:
            return False
        if request.method in SAFE_METHODS:
            return True
        return role in (Role.OPS, Role.SALES, Role.PARTNER)


class TravellerPermission(BasePermission):
    message = "Your role may not manage travellers."

    def has_permission(self, request: Request, view) -> bool:  # noqa: ANN001
        role = _role(request)
        if role is None:
            return False
        if request.method in SAFE_METHODS:
            return role in (Role.OPS, Role.SALES, Role.PARTNER, Role.FINANCE)
        return role in (Role.OPS, Role.SALES, Role.PARTNER)
