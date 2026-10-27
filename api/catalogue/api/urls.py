from rest_framework.routers import SimpleRouter

from .views import DepartureViewSet, DestinationTypeViewSet, DestinationViewSet, PackageViewSet

router = SimpleRouter(trailing_slash=False)
router.register("destination-types", DestinationTypeViewSet, basename="destination-type")
router.register("destinations", DestinationViewSet, basename="destination")
router.register("packages", PackageViewSet, basename="package")
router.register("departures", DepartureViewSet, basename="departure")

urlpatterns = router.urls
