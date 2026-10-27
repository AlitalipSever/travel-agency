"""Root URL map.

Health at the root for Kubernetes probes; the OpenAPI schema and Swagger UI under /api; the
versioned API under /api/v1 (added app by app); the admin for operations.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", include("core.urls")),
    path("admin/", admin.site.urls),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
