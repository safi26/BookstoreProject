from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from .models import (
    Cart,
    CartItem,
    CashDrawer,
    Category,
    Item,
    Sale,
    StaffCredential,
    StudentId,
    Voucher,
)


class VoucherModelTests(APITestCase):
    def test_voucher_amount_must_be_positive(self):
        for balance in (Decimal("0.00"), Decimal("-5.00")):
            with self.subTest(balance=balance):
                with self.assertRaises(ValidationError):
                    Voucher(voucher_id="V-BAD", balance=balance).full_clean()

        Voucher(voucher_id="V-GOOD", balance=Decimal("0.01")).full_clean()

    def test_database_rejects_negative_balance(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Voucher.objects.create(voucher_id="V-NEG", balance=Decimal("-1.00"))

    def test_voucher_and_student_ids_cannot_overlap(self):
        StudentId.objects.create(student_id="SHARED-1")
        with self.assertRaises(ValidationError):
            Voucher(voucher_id="SHARED-1", balance=Decimal("10.00")).full_clean()

        Voucher.objects.create(voucher_id="SHARED-2", balance=Decimal("10.00"))
        with self.assertRaises(ValidationError):
            StudentId(student_id="SHARED-2").full_clean()


class VoucherCheckoutTests(APITestCase):
    TOTAL = "27.06"

    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="voucher-student",
            password="student-password",
        )
        self.staff_user = user_model.objects.create_user(
            username="voucher-staff",
            password="staff-password",
        )
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.staff_user.groups.add(manager_group)
        credential = StaffCredential(user=self.staff_user)
        credential.set_pin("5173")
        credential.save()
        self.client.force_authenticate(user=self.user)
        self.staff_authorization = self.client.post(
            "/api/auth/staff/verify-pin/",
            {"staff_id": self.staff_user.pk, "pin": "5173"},
            format="json",
        ).data["staff_authorization"]

        category = Category.objects.create(category_name="Voucher tests")
        self.item = Item.objects.create(
            item="Voucher Book",
            item_quantity=8,
            item_price=Decimal("12.50"),
            item_code="BK-VOUCHER",
            category=category,
        )
        cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=cart, item=self.item, quantity=2)

        self.full_voucher = Voucher.objects.create(voucher_id="V-FULL", balance=Decimal("50.00"))
        self.partial_voucher = Voucher.objects.create(voucher_id="V-PART", balance=Decimal("10.00"))
        self.inactive_voucher = Voucher.objects.create(
            voucher_id="V-OFF",
            balance=Decimal("50.00"),
            is_active=False,
        )
        self.cart_url = f"/api/users/{self.user.pk}/cart/"
        self.checkout_url = f"/api/users/{self.user.pk}/checkout/"

    def staff_headers(self):
        return {"HTTP_X_STAFF_AUTHORIZATION": self.staff_authorization}

    def cart(self, voucher_id):
        return self.client.get(self.cart_url, {"student_id": voucher_id}, **self.staff_headers())

    def checkout(self, voucher_id, payment_method, **extra):
        return self.client.post(
            self.checkout_url,
            {"student_id": voucher_id, "payment_method": payment_method, **extra},
            format="json",
            **self.staff_headers(),
        )

    def assert_nothing_changed(self, voucher, balance):
        voucher.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(voucher.balance, Decimal(balance))
        self.assertEqual(self.item.item_quantity, 8)
        self.assertFalse(Sale.objects.exists())
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

    def test_voucher_entry_requires_staff_pin(self):
        response = self.client.get(self.cart_url, {"student_id": "V-FULL"})

        self.assertEqual(response.status_code, 403)

    def test_cart_preview_shows_voucher_covering_full_total(self):
        response = self.cart("V-FULL")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["customer_discount_type"], "")
        self.assertEqual(f"{response.data['total_price']}", self.TOTAL)
        self.assertEqual(response.data["voucher_id"], "V-FULL")
        self.assertEqual(f"{response.data['voucher_amount']}", self.TOTAL)
        self.assertEqual(f"{response.data['amount_due']}", "0.00")

    def test_cart_preview_shows_remaining_amount_due(self):
        response = self.cart("V-PART")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(f"{response.data['voucher_balance']}", "10.00")
        self.assertEqual(f"{response.data['voucher_amount']}", "10.00")
        self.assertEqual(f"{response.data['amount_due']}", "17.06")

    def test_voucher_pays_full_total(self):
        response = self.checkout("V-FULL", "voucher")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_method"], "voucher")
        self.assertEqual(response.data["voucher_code"], "V-FULL")
        self.assertEqual(response.data["voucher_amount"], self.TOTAL)
        self.assertEqual(response.data["total"], self.TOTAL)
        self.assertIsNone(response.data["cash_received"])
        self.full_voucher.refresh_from_db()
        self.assertEqual(self.full_voucher.balance, Decimal("22.94"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_quantity, 6)

    def test_fully_covered_cash_checkout_takes_no_cash(self):
        response = self.checkout("V-FULL", "cash", cash_received="40.00")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_method"], "voucher")
        self.assertIsNone(response.data["cash_received"])
        self.assertFalse(CashDrawer.objects.filter(balance__gt=0).exists())

    def test_partial_voucher_cannot_pay_alone(self):
        response = self.checkout("V-PART", "voucher")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["amount_due"], "17.06")
        self.assertIn("remaining $17.06 by cash or card", response.data["error"])
        self.assert_nothing_changed(self.partial_voucher, "10.00")

    def test_partial_voucher_with_card_covers_remaining(self):
        response = self.checkout("V-PART", "card")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_method"], "card")
        self.assertEqual(response.data["voucher_amount"], "10.00")
        self.assertEqual(response.data["total"], self.TOTAL)
        self.partial_voucher.refresh_from_db()
        self.assertEqual(self.partial_voucher.balance, Decimal("0.00"))

    def test_partial_voucher_with_cash_gives_change_on_remaining(self):
        response = self.checkout("V-PART", "cash", cash_received="20.00")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["voucher_amount"], "10.00")
        self.assertEqual(response.data["cash_received"], "20.00")
        self.assertEqual(response.data["change_due"], "2.94")
        self.assertEqual(CashDrawer.objects.get(pk=1).balance, Decimal("17.06"))

    def test_cash_must_cover_remaining_amount(self):
        response = self.checkout("V-PART", "cash", cash_received="17.05")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Cash received must cover the amount due.")
        self.assert_nothing_changed(self.partial_voucher, "10.00")

    def test_spent_voucher_is_rejected(self):
        self.checkout("V-PART", "card")
        CartItem.objects.create(cart=self.cart_item.cart, item=self.item, quantity=1)

        response = self.cart("V-PART")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "This voucher has no remaining balance.")

    def test_inactive_or_unknown_voucher_is_rejected(self):
        for voucher_id in ("V-OFF", "V-NOPE"):
            with self.subTest(voucher_id=voucher_id):
                response = self.checkout(voucher_id, "card")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["error"],
                    "Enter a valid student ID or voucher ID.",
                )
                self.assert_nothing_changed(self.inactive_voucher, "50.00")

    def test_pay_by_voucher_needs_a_voucher(self):
        response = self.client.post(
            self.checkout_url,
            {"payment_method": "voucher"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Sale.objects.exists())

    def test_voucher_does_not_give_student_discount(self):
        response = self.checkout("V-FULL", "voucher")

        self.assertEqual(response.data["customer_discount_type"], "")
        self.assertEqual(response.data["customer_discount_amount"], "0.00")
