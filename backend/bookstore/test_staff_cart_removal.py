from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import (
    Cart,
    CartItem,
    Category,
    Item,
    StaffCartItemPriceChange,
    StaffCartItemRemoval,
    StaffCredential,
)


class StaffCartItemRemovalApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.shopper = user_model.objects.create_user(username="removal-shopper")
        self.staff = user_model.objects.create_user(
            username="removal-manager",
            is_staff=True,
        )
        credential = StaffCredential(user=self.staff)
        credential.set_pin("4826")
        credential.save()
        category = Category.objects.create(category_name="Removal test")
        item = Item.objects.create(
            item="Removal test item",
            item_quantity=8,
            item_price=Decimal("10.00"),
            item_code="RM-001",
            category=category,
        )
        cart = Cart.objects.create(user=self.shopper)
        self.cart_item = CartItem.objects.create(cart=cart, item=item, quantity=2)
        self.client.force_authenticate(user=self.shopper)
        self.url = (
            f"/api/users/{self.shopper.pk}/cart/items/"
            f"{self.cart_item.pk}/staff-remove/"
        )
        self.price_change_url = (
            f"/api/users/{self.shopper.pk}/cart/items/"
            f"{self.cart_item.pk}/staff-price-change/"
        )

    def get_staff_authorization(self):
        response = self.client.post(
            "/api/auth/staff/verify-pin/",
            {"staff_id": self.staff.pk, "pin": "4826"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        return response.data["staff_authorization"]

    def test_staff_pin_is_required_and_item_remains_when_missing(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())
        self.assertFalse(StaffCartItemRemoval.objects.exists())

    def test_removal_is_recorded_with_staff_id_and_timestamp(self):
        authorization = self.get_staff_authorization()

        response = self.client.post(
            self.url,
            {},
            format="json",
            HTTP_X_STAFF_AUTHORIZATION=authorization,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["staff_id"], self.staff.pk)
        self.assertTrue(response.data["removed_at"])
        self.assertEqual(response.data["quantity_removed"], 2)
        self.assertFalse(CartItem.objects.filter(pk=self.cart_item.pk).exists())
        audit = StaffCartItemRemoval.objects.get()
        self.assertEqual(audit.student_user_id, self.shopper.pk)
        self.assertEqual(audit.staff_user_id, self.staff.pk)
        self.assertEqual(audit.item_name, "Removal test item")
        self.assertEqual(audit.item_code, "RM-001")
        self.assertEqual(audit.quantity_removed, 2)
        self.assertIsNotNone(audit.removed_at)

    def test_staff_price_change_updates_catalog_and_cart_and_records_audit(self):
        authorization = self.get_staff_authorization()

        response = self.client.post(
            self.price_change_url,
            {"new_price": "7.50", "reason": "Damaged packaging"},
            format="json",
            HTTP_X_STAFF_AUTHORIZATION=authorization,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["staff_id"], self.staff.pk)
        self.assertEqual(response.data["original_price"], Decimal("10.00"))
        self.assertEqual(response.data["new_price"], Decimal("7.50"))
        self.assertEqual(response.data["reason"], "Damaged packaging")
        self.assertTrue(response.data["changed_at"])

        self.cart_item.item.refresh_from_db()
        self.assertEqual(self.cart_item.item.item_price, Decimal("7.50"))
        cart_response = self.client.get(f"/api/users/{self.shopper.pk}/cart/")
        self.assertEqual(cart_response.status_code, 200)
        self.assertEqual(cart_response.data["cart_items"][0]["item_price"], "7.50")

        audit = StaffCartItemPriceChange.objects.get()
        self.assertEqual(audit.student_user_id, self.shopper.pk)
        self.assertEqual(audit.staff_user_id, self.staff.pk)
        self.assertEqual(audit.item_name, "Removal test item")
        self.assertEqual(audit.original_price, Decimal("10.00"))
        self.assertEqual(audit.new_price, Decimal("7.50"))
        self.assertEqual(audit.reason, "Damaged packaging")
        self.assertIsNotNone(audit.changed_at)

    def test_price_change_requires_staff_authorization_and_reason(self):
        unauthorized = self.client.post(
            self.price_change_url,
            {"new_price": "7.50", "reason": "Price adjustment"},
            format="json",
        )
        self.assertEqual(unauthorized.status_code, 403)
        self.assertEqual(self.cart_item.item.item_price, Decimal("10.00"))

        authorization = self.get_staff_authorization()
        missing_reason = self.client.post(
            self.price_change_url,
            {"new_price": "7.50", "reason": "  "},
            format="json",
            HTTP_X_STAFF_AUTHORIZATION=authorization,
        )

        self.assertEqual(missing_reason.status_code, 400)
        self.assertIn("reason", missing_reason.data)
        self.assertFalse(StaffCartItemPriceChange.objects.exists())
