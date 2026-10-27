"""RFC 7807 problem details for every non-2xx response (04-api §1, N6.4).

One exception handler turns DRF and Django exceptions, and our own ProblemError family, into
the same envelope: type, title, status, detail, instance, and errors[] for validation. Internals
are never echoed; unexpected errors become a generic 500 problem.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, HttpRequest, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

log = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"


class ProblemType:
    """URIs under /problems/, the closed catalogue of 04-api §1."""

    VALIDATION = "/problems/validation"
    UNAUTHENTICATED = "/problems/unauthenticated"
    FORBIDDEN = "/problems/forbidden"
    NOT_FOUND = "/problems/not-found"
    CONFLICT = "/problems/conflict"
    IDEMPOTENCY_MISMATCH = "/problems/idempotency-mismatch"
    RATE_LIMITED = "/problems/rate-limited"
    UPSTREAM_UNAVAILABLE = "/problems/upstream-unavailable"
    METHOD_NOT_ALLOWED = "/problems/method-not-allowed"
    INTERNAL = "/problems/internal"


class ProblemError(Exception):
    """Base for the errors our services raise; subclasses fix type, title and status."""

    type: str = ProblemType.INTERNAL
    title: str = "Internal error"
    status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        detail: str,
        *,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.data = data or {}
        self.headers = headers or {}


class Conflict(ProblemError):
    type = ProblemType.CONFLICT
    title = "Conflict"
    status = status.HTTP_409_CONFLICT


class IdempotencyMismatch(ProblemError):
    type = ProblemType.IDEMPOTENCY_MISMATCH
    title = "Idempotency key reused with a different request"
    status = status.HTTP_422_UNPROCESSABLE_ENTITY


class RateLimited(ProblemError):
    type = ProblemType.RATE_LIMITED
    title = "Rate limited"
    status = status.HTTP_429_TOO_MANY_REQUESTS


class UpstreamUnavailable(ProblemError):
    type = ProblemType.UPSTREAM_UNAVAILABLE
    title = "Weather upstream unavailable"
    status = status.HTTP_503_SERVICE_UNAVAILABLE


def _problem(
    *, type_: str, title: str, status_code: int, detail: str, instance: str, **extra: Any
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


def _flatten_validation(detail: Any, prefix: str = "") -> list[dict[str, str]]:
    """DRF nests field errors arbitrarily; flatten to [{field, message}] (04 §1)."""
    errors: list[dict[str, str]] = []
    if isinstance(detail, dict):
        for field, value in detail.items():
            name = f"{prefix}.{field}" if prefix else str(field)
            errors.extend(_flatten_validation(value, name))
    elif isinstance(detail, list):
        for item in detail:
            errors.extend(_flatten_validation(item, prefix))
    else:
        errors.append({"field": prefix or "non_field", "message": str(detail)})
    return errors


_DRF_TYPES: dict[type[exceptions.APIException], tuple[str, str]] = {
    exceptions.ValidationError: (ProblemType.VALIDATION, "Validation failed"),
    exceptions.ParseError: (ProblemType.VALIDATION, "Malformed request"),
    exceptions.NotAuthenticated: (ProblemType.UNAUTHENTICATED, "Authentication required"),
    exceptions.AuthenticationFailed: (ProblemType.UNAUTHENTICATED, "Authentication failed"),
    exceptions.PermissionDenied: (ProblemType.FORBIDDEN, "Not allowed for this role"),
    exceptions.NotFound: (ProblemType.NOT_FOUND, "Not found"),
    exceptions.MethodNotAllowed: (ProblemType.METHOD_NOT_ALLOWED, "Method not allowed"),
    exceptions.Throttled: (ProblemType.RATE_LIMITED, "Rate limited"),
}


def problem_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF EXCEPTION_HANDLER: every handled exception leaves as a problem+json body."""
    request = context.get("request")
    instance = request.get_full_path() if request is not None else ""

    if isinstance(exc, ProblemError):
        body = _problem(
            type_=exc.type,
            title=exc.title,
            status_code=exc.status,
            detail=exc.detail,
            instance=instance,
            **exc.data,
        )
        response = Response(body, status=exc.status, headers=exc.headers)
        response.content_type = PROBLEM_CONTENT_TYPE
        return response

    # Django's own exceptions arrive here too; DRF maps them before we see them.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:  # not an API exception: let Django produce the 500 (handler500)
        return None

    assert isinstance(exc, exceptions.APIException)
    type_, title = _DRF_TYPES.get(type(exc), (ProblemType.INTERNAL, "Error"))
    for klass, mapping in _DRF_TYPES.items():  # subclasses, e.g. custom ValidationErrors
        if isinstance(exc, klass):
            type_, title = mapping
            break

    extra: dict[str, Any] = {}
    detail: str
    if isinstance(exc, exceptions.ValidationError):
        extra["errors"] = _flatten_validation(exc.detail)
        detail = "One or more fields are invalid."
    else:
        detail = str(exc.detail) if not isinstance(exc.detail, list | dict) else title

    response.data = _problem(
        type_=type_,
        title=title,
        status_code=response.status_code,
        detail=detail,
        instance=instance,
        **extra,
    )
    response.content_type = PROBLEM_CONTENT_TYPE
    return response


# Django-level handlers: errors raised outside any DRF view (no URL matched, CSRF, the last
# resort 500). Registered in config/urls.py as handler400, handler403, handler404, handler500.


def _django_problem(
    request: HttpRequest, *, type_: str, title: str, status_code: int, detail: str
) -> JsonResponse:
    body = _problem(
        type_=type_,
        title=title,
        status_code=status_code,
        detail=detail,
        instance=request.get_full_path(),
    )
    return JsonResponse(body, status=status_code, content_type=PROBLEM_CONTENT_TYPE)


def handler400(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _django_problem(
        request,
        type_=ProblemType.VALIDATION,
        title="Bad request",
        status_code=400,
        detail="The request could not be understood.",
    )


def handler403(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _django_problem(
        request,
        type_=ProblemType.FORBIDDEN,
        title="Forbidden",
        status_code=403,
        detail="Not allowed.",
    )


def handler404(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _django_problem(
        request,
        type_=ProblemType.NOT_FOUND,
        title="Not found",
        status_code=404,
        detail="No resource at this path.",
    )


def handler500(request: HttpRequest) -> JsonResponse:
    """Django's last resort: a generic problem, nothing about the failure itself (N6.4)."""
    log.exception("unhandled error on %s", request.get_full_path())
    return _django_problem(
        request,
        type_=ProblemType.INTERNAL,
        title="Internal error",
        status_code=500,
        detail="The request could not be processed.",
    )
