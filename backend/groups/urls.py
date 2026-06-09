from rest_framework.routers import DefaultRouter

from .views import GrupaViewSet

router = DefaultRouter()
router.register("", GrupaViewSet, basename="group")

urlpatterns = router.urls
