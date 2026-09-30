from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ItemViewSet,
    CartView,
    CartItemCreateView,
    CartItemDetailView,
    CheckoutView,
)


router = DefaultRouter()

router.register(
    "categories",
    CategoryViewSet,
    basename="category",
)

router.register(
    "items",
    ItemViewSet,
    basename="item",
)


urlpatterns = [
    path(
        "users/<int:user_id>/cart/",
        CartView.as_view(),
        name="cart",
    ),

    path(
        "users/<int:user_id>/cart/items/",
        CartItemCreateView.as_view(),
        name="cart-item-create",
    ),

    path(
        "users/<int:user_id>/cart/items/<int:cart_item_id>/",
        CartItemDetailView.as_view(),
        name="cart-item-detail",
    ),

    path(
        "users/<int:user_id>/checkout/",
        CheckoutView.as_view(),
        name="checkout",
    ),
]

urlpatterns += router.urls