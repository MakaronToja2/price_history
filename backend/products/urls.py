from django.urls import path

from .views import GroupProductsView

urlpatterns = [
    path(
        "groups/<int:group_id>/products/",
        GroupProductsView.as_view(),
        name="group-products",
    ),
]
