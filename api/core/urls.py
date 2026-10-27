from django.urls import path

from .views import HealthzView, ReadyzView

urlpatterns = [
    path("healthz", HealthzView.as_view(), name="healthz"),
    path("readyz", ReadyzView.as_view(), name="readyz"),
]
