from django.urls import path

from .views import CurrentWeatherView, ForecastView, OpsStatusView

urlpatterns = [
    path("weather/current", CurrentWeatherView.as_view(), name="weather-current"),
    path("weather/forecast", ForecastView.as_view(), name="weather-forecast"),
    path("ops/status", OpsStatusView.as_view(), name="ops-status"),
]
