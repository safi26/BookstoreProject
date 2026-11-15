from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    CourseSupplyBundleViewSet,
    ItemViewSet,
    ItemVariantCollectionView,
    ItemVariantDetailView,
    SaleViewSet,
    CartView,
    CartItemCreateView,
    CartItemDetailView,
    CheckoutView,
    CashDrawerView,
    DailySalesReportView,
    BestSellingItemsReportView,
    LoginView,
    LogoutView,
    StaffPinVerificationView,
    StaffCartItemRemovalView,
    StaffCartItemPriceChangeView,
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
    "bundles",
    CourseSupplyBundleViewSet,
    basename="course-supply-bundle",
)

router.register(
    "sales",
    SaleViewSet,
    basename="sale",
)


urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/staff/verify-pin/", StaffPinVerificationView.as_view(), name="api-staff-pin-verify"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("cash-drawer/", CashDrawerView.as_view(), name="cash-drawer"),
    path("reports/daily-sales/", DailySalesReportView.as_view(), name="daily-sales-report"),
    path("reports/best-selling-items/", BestSellingItemsReportView.as_view(), name="best-selling-items-report"),
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
        "users/<int:user_id>/cart/items/<int:cart_item_id>/staff-remove/",
        StaffCartItemRemovalView.as_view(),
        name="staff-cart-item-removal",
    ),
    path(
        "users/<int:user_id>/cart/items/<int:cart_item_id>/staff-price-change/",
        StaffCartItemPriceChangeView.as_view(),
        name="staff-cart-item-price-change",
    ),

    path(
        "users/<int:user_id>/checkout/",
        CheckoutView.as_view(),
        name="checkout",
    ),
]

urlpatterns += router.urls