from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from .models import Cart, CartItem, CashDrawer, Category, Item, StaffCredential


class CashDrawerApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.student = user_model.objects.create_user(
            username="drawer-student",
            password="student-password",
        )
        self.manager = user_model.objects.create_user(
            username="drawer-manager",
            password="manager-password",
        )
        self.operator = user_model.objects.create_user(
            username="drawer-operator",
            password="operator-password",
        )
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        operator_group, _ = Group.objects.get_or_create(name="Operator")
        self.manager.groups.add(manager_group)
        self.operator.groups.add(operator_group)
        staff_credential = StaffCredential(user=self.manager)
        staff_credential.set_pin("4826")
        staff_credential.save()
        self.client.force_authenticate(user=self.student)
        self.staff_authorization = self.client.post(
            "/api/auth/staff/verify-pin/",
            {"staff_id": self.manager.pk, "pin": "4826"},
            format="json",
        ).data["staff_authorization"]

        category = Category.objects.create(category_name="Drawer tests")
        item = Item.objects.create(
            item="Cash drawer test item",
            item_quantity=10,
            item_price=Decimal("10.00"),
            category=category,
        )
        cart = Cart.objects.create(user=self.student)
        CartItem.objects.create(cart=cart, item=item, quantity=1)
        self.url = "/api/cash-drawer/"
        self.checkout_url = f"/api/users/{self.student.pk}/checkout/"

    def test_manager_sets_opening_balance_and_threshold(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            self.url,
            {"balance": "20.00", "low_change_threshold": "25.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["balance"], "20.00")
        self.assertEqual(response.data["low_change_threshold"], "25.00")
        self.assertTrue(response.data["is_low"])

    def test_only_staff_can_read_and_only_managers_can_update(self):
        self.client.force_authenticate(user=self.student)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        verified_read = self.client.get(
            self.url,
            HTTP_X_STAFF_AUTHORIZATION=self.staff_authorization,
        )
        self.assertEqual(verified_read.status_code, 200)
        self.client.force_authenticate(user=self.student)
        invalid_verified_read = self.client.get(
            self.url,
            HTTP_X_STAFF_AUTHORIZATION="not-a-valid-staff-token",
        )
        self.assertEqual(invalid_verified_read.status_code, 403)

        self.client.force_authenticate(user=self.operator)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(
            self.client.patch(self.url, {"balance": "10.00"}, format="json").status_code,
            403,
        )

    def test_negative_drawer_amounts_are_rejected(self):
        self.client.force_authenticate(user=self.manager)
        initial = self.client.get(self.url)

        response = self.client.patch(
            self.url,
            {"low_change_threshold": "-1.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        drawer = CashDrawer.objects.get(pk=1)
        self.assertEqual(drawer.balance, Decimal(initial.data["balance"]))
        self.assertEqual(
            drawer.low_change_threshold,
            Decimal(initial.data["low_change_threshold"]),
        )

    def test_cash_checkout_updates_balance_by_cash_received_less_change(self):
        drawer = CashDrawer.objects.create(
            pk=1,
            balance=Decimal("20.00"),
            low_change_threshold=Decimal("40.00"),
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.checkout_url,
            {"payment_method": "cash", "cash_received": "20.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["change_due"], "9.17")
        drawer.refresh_from_db()
        self.assertEqual(drawer.balance, Decimal("30.83"))
        self.assertTrue(drawer.balance < drawer.low_change_threshold)

    def test_card_checkout_does_not_change_drawer_balance(self):
        drawer = CashDrawer.objects.create(
            pk=1,
            balance=Decimal("20.00"),
            low_change_threshold=Decimal("15.00"),
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self.checkout_url,
            {"payment_method": "card"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        drawer.refresh_from_db()
        self.assertEqual(drawer.balance, Decimal("20.00"))
