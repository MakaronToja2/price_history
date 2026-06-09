from django.urls import path

from .views import GroupProductDetailView, GroupProductsView

urlpatterns = [
    path(
        "groups/<int:group_id>/products/",
        GroupProductsView.as_view(),
        name="group-products",
    ),
    path(
        "groups/<int:group_id>/products/<int:product_id>/",
        GroupProductDetailView.as_view(),
        name="group-product-detail",
    ),
]
