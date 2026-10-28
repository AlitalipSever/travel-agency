from rest_framework.routers import SimpleRouter

from .views import LocationViewSet

router = SimpleRouter(trailing_slash=False)
router.register("locations", LocationViewSet, basename="location")

urlpatterns = router.urls
