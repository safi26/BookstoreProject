from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Cart, CartItem, Category, Item, Sale, SaleItem


class CheckoutApiTests(APITestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="checkout-student",
			password="test-password",
		)
		category = Category.objects.create(category_name="Fiction")
		self.item = Item.objects.create(
			item="Test Book",
			item_quantity=8,
			item_price=Decimal("12.50"),
			author="Test Author",
			item_code="BK-TEST",
			category=category,
		)
		cart = Cart.objects.create(user=self.user)
		CartItem.objects.create(cart=cart, item=self.item, quantity=2)
		self.url = f"/api/users/{self.user.pk}/checkout/"

	def test_cash_checkout_records_receipt_change_and_stock(self):
		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "30.00"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["total"], "25.00")
		self.assertEqual(response.data["cash_received"], "30.00")
		self.assertEqual(response.data["change_due"], "5.00")
		self.assertEqual(response.data["items"][0]["item_name"], "Test Book")
		self.assertEqual(response.data["items"][0]["line_total"], "25.00")
		self.assertEqual(Sale.objects.count(), 1)
		self.assertEqual(SaleItem.objects.get().quantity, 2)
		self.item.refresh_from_db()
		self.assertEqual(self.item.item_quantity, 6)
		self.assertEqual(CartItem.objects.count(), 0)

	def test_insufficient_cash_preserves_cart_and_stock(self):
		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "24.99"},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Sale.objects.count(), 0)
		self.assertEqual(CartItem.objects.get().quantity, 2)
		self.item.refresh_from_db()
		self.assertEqual(self.item.item_quantity, 8)

	def test_card_demo_checkout_records_sale_without_card_data(self):
		response = self.client.post(
			self.url,
			{"payment_method": "card"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["payment_method"], "card")
		self.assertIsNone(response.data["cash_received"])
		self.assertEqual(response.data["change_due"], "0.00")
		self.assertEqual(response.data["total"], "25.00")
