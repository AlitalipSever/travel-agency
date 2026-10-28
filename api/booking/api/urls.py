from rest_framework.routers import SimpleRouter

from .views import BookingViewSet, TravellerViewSet

router = SimpleRouter(trailing_slash=False)
router.register("travellers", TravellerViewSet, basename="traveller")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = router.urls
