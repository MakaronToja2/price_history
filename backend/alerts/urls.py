from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AlertViewSet, GrupaAlertsView

router = DefaultRouter()
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    *router.urls,
    path(
        "groups/<int:group_id>/alerts/",
        GrupaAlertsView.as_view(),
        name="group-alerts",
    ),
]
