from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import Cart, CartItem, Category, Item, Sale, StaffCredential, StudentId


class StaffPinVerificationApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.shopper = user_model.objects.create_user(
            username="pin-shopper",
            password="shopper-password",
        )
        self.manager = user_model.objects.create_user(
            username="pin-manager",
            password="manager-password",
        )
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.manager.groups.add(manager_group)
        credential = StaffCredential(user=self.manager)
        credential.set_pin("0042")
        credential.save()
        self.client.force_authenticate(user=self.shopper)

        self.category = Category.objects.create(category_name="PIN test")
        self.item = Item.objects.create(
            item="PIN test item",
            item_quantity=8,
            item_price=Decimal("10.00"),
            category=self.category,
        )
        cart = Cart.objects.create(user=self.shopper)
        CartItem.objects.create(cart=cart, item=self.item, quantity=1)
        StudentId.objects.create(student_id="PIN-STUDENT")
        self.cart_url = f"/api/users/{self.shopper.pk}/cart/"
        self.checkout_url = f"/api/users/{self.shopper.pk}/checkout/"

    def verify_staff_pin(self, staff_id=None, pin="0042"):
        return self.client.post(
            "/api/auth/staff/verify-pin/",
            {"staff_id": staff_id or self.manager.pk, "pin": pin},
            format="json",
        )

    def test_wrong_credentials_return_clear_error(self):
        response = self.verify_staff_pin(pin="9999")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Invalid staff ID or PIN.")
        self.assertNotIn("staff_authorization", response.data)

    def test_staff_pin_attempts_are_rate_limited(self):
        for _ in range(5):
            response = self.verify_staff_pin(pin="9999")
            self.assertEqual(response.status_code, 400)

        throttled = self.verify_staff_pin(pin="9999")

        self.assertEqual(throttled.status_code, 429)

    def test_student_cannot_verify_as_staff(self):
        response = self.verify_staff_pin(staff_id=self.shopper.pk)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Invalid staff ID or PIN.")

    def test_student_id_discount_requires_staff_verification(self):
        response = self.client.get(self.cart_url, {"student_id": "PIN-STUDENT"})

        self.assertEqual(response.status_code, 403)
        self.assertIn("Staff ID and PIN", response.data["detail"])

    def test_checkout_rejects_discount_without_staff_verification(self):
        response = self.client.post(
            self.checkout_url,
            {"payment_method": "card", "student_id": "PIN-STUDENT"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Sale.objects.exists())
        self.assertTrue(CartItem.objects.filter(cart__user=self.shopper).exists())

    def test_valid_staff_pin_authorizes_discount_for_shopper_cart(self):
        verification = self.verify_staff_pin()
        self.assertEqual(verification.status_code, 200)

        authorization = verification.data["staff_authorization"]
        preview = self.client.get(
            self.cart_url,
            {"student_id": "PIN-STUDENT"},
            HTTP_X_STAFF_AUTHORIZATION=authorization,
        )
        checkout = self.client.post(
            self.checkout_url,
            {"payment_method": "card", "student_id": "PIN-STUDENT"},
            format="json",
            HTTP_X_STAFF_AUTHORIZATION=authorization,
        )

        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["customer_discount_type"], "student")
        self.assertEqual(checkout.status_code, 201)
        self.assertEqual(checkout.data["customer_discount_type"], "student")
        self.assertEqual(checkout.data["customer_discount_amount"], "1.00")
        self.assertEqual(checkout.data["total"], "9.74")
        self.assertEqual(checkout.data["items"][0]["item_name"], "PIN test item")
        self.assertEqual(self.shopper.pk, checkout.wsgi_request.user.pk)

    def test_tampered_staff_authorization_is_rejected(self):
        authorization = self.verify_staff_pin().data["staff_authorization"] + "x"
        response = self.client.get(
            self.cart_url,
            {"student_id": "PIN-STUDENT"},
            HTTP_X_STAFF_AUTHORIZATION=authorization,
        )

        self.assertEqual(response.status_code, 403)
