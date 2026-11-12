from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ItemViewSet,
    ItemVariantCollectionView,
    ItemVariantDetailView,
    SaleViewSet,
    CartView,
    CartItemCreateView,
    CartItemDetailView,
    CheckoutView,
    LoginView,
    LogoutView,
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

router.register(
    "sales",
    SaleViewSet,
    basename="sale",
)


urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path(
        "items/<int:item_id>/variants/",
        ItemVariantCollectionView.as_view(),
        name="item-variants",
    ),
    path(
        "items/<int:item_id>/variants/<int:variant_id>/",
        ItemVariantDetailView.as_view(),
        name="item-variant-detail",
    ),
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