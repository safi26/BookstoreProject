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

	def test_standard_checkout_records_tax_and_stock(self):
		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "30.00"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["subtotal"], "25.00")
		self.assertEqual(response.data["tax_amount"], "2.06")
		self.assertEqual(response.data["total"], "27.06")
		self.assertEqual(response.data["cash_received"], "30.00")
		self.assertEqual(response.data["change_due"], "2.94")
		self.assertEqual(response.data["items"][0]["item_name"], "Test Book")
		self.assertEqual(response.data["items"][0]["line_total"], "25.00")
		self.assertEqual(response.data["items"][0]["tax_amount"], "2.06")
		self.assertEqual(Sale.objects.count(), 1)
		self.assertEqual(Sale.objects.get().tax_amount, Decimal("2.06"))
		self.assertEqual(SaleItem.objects.get().quantity, 2)
		self.item.refresh_from_db()
		self.assertEqual(self.item.item_quantity, 6)
		self.assertEqual(CartItem.objects.count(), 0)

	def test_receipt_breaks_tax_down_per_taxable_and_exempt_item(self):
		category = self.item.category
		taxable_item = Item.objects.create(
			item="Taxable Item",
			item_quantity=5,
			item_price=Decimal("10.00"),
			category=category,
		)
		exempt_item = Item.objects.create(
			item="Exempt Item",
			item_quantity=5,
			item_price=Decimal("5.00"),
			tax_exempt=True,
			category=category,
		)
		CartItem.objects.filter(item=self.item).update(quantity=1)
		cart = Cart.objects.get(user=self.user)
		CartItem.objects.create(cart=cart, item=taxable_item, quantity=1)
		CartItem.objects.create(cart=cart, item=exempt_item, quantity=1)

		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "30.00"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["subtotal"], "27.50")
		self.assertEqual(response.data["tax_amount"], "1.86")
		self.assertEqual(response.data["total"], "29.36")
		items_by_name = {
			item["item_name"]: item
			for item in response.data["items"]
		}
		self.assertEqual(items_by_name["Test Book"]["tax_amount"], "1.03")
		self.assertEqual(items_by_name["Taxable Item"]["tax_amount"], "0.83")
		self.assertEqual(items_by_name["Exempt Item"]["tax_amount"], "0.00")

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

	def test_card_demo_checkout_records_sale_without_storing_card_data(self):
		response = self.client.post(
			self.url,
			{"payment_method": "card"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["payment_method"], "card")
		self.assertIsNone(response.data["cash_received"])
		self.assertEqual(response.data["change_due"], "0.00")
		self.assertEqual(response.data["total"], "27.06")
		self.assertNotIn("card_number", response.data)
		self.assertEqual(Sale.objects.count(), 1)
		self.assertEqual(CartItem.objects.count(), 0)

	def test_snack_checkout_charges_tax_and_includes_it_in_cash_total(self):
		self.item.category = Category.objects.create(category_name="Snacks")
		self.item.save(update_fields=["category"])

		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "28.00"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["subtotal"], "25.00")
		self.assertEqual(response.data["tax_amount"], "2.06")
		self.assertEqual(response.data["total"], "27.06")
		self.assertEqual(response.data["change_due"], "0.94")
		self.assertEqual(response.data["items"][0]["tax_amount"], "2.06")
		sale = Sale.objects.get()
		self.assertEqual(sale.subtotal, Decimal("25.00"))
		self.assertEqual(sale.tax_amount, Decimal("2.06"))
		self.assertEqual(sale.total, Decimal("27.06"))

	def test_cash_must_cover_tax_inclusive_total(self):
		self.item.category = Category.objects.create(category_name="Snacks")
		self.item.save(update_fields=["category"])

		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "27.05"},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Sale.objects.count(), 0)
		self.assertEqual(CartItem.objects.get().quantity, 2)
		self.item.refresh_from_db()
		self.assertEqual(self.item.item_quantity, 8)

	def test_drink_checkout_charges_tax(self):
		self.item.category = Category.objects.create(category_name="Drinks")
		self.item.save(update_fields=["category"])

		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "27.06"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["tax_amount"], "2.06")
		self.assertEqual(response.data["total"], "27.06")

	def test_tax_exempt_item_is_not_taxed(self):
		snacks = Category.objects.create(category_name="Snacks")
		self.item.category = snacks
		self.item.tax_exempt = True
		self.item.save(update_fields=["category", "tax_exempt"])

		item_exempt_response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "25.00"},
			format="json",
		)
		self.assertEqual(item_exempt_response.status_code, 201)
		self.assertEqual(item_exempt_response.data["tax_amount"], "0.00")
		self.assertEqual(item_exempt_response.data["total"], "25.00")

	def test_tax_exempt_category_is_not_taxed(self):
		snacks = Category.objects.create(category_name="Snacks", tax_exempt=True)
		self.item.category = snacks
		self.item.save(update_fields=["category"])

		category_exempt_response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "25.00"},
			format="json",
		)
		self.assertEqual(category_exempt_response.status_code, 201)
		self.assertEqual(category_exempt_response.data["tax_amount"], "0.00")
		self.assertEqual(category_exempt_response.data["total"], "25.00")

	def test_cart_reports_subtotal_tax_and_tax_inclusive_total(self):
		self.item.category = Category.objects.create(category_name="Snacks")
		self.item.save(update_fields=["category"])

		response = self.client.get(f"/api/users/{self.user.pk}/cart/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["subtotal"], Decimal("25.00"))
		self.assertEqual(response.data["tax_amount"], Decimal("2.06"))
		self.assertEqual(response.data["total_price"], Decimal("27.06"))
		self.assertEqual(response.data["cart_items"][0]["tax_amount"], Decimal("2.06"))

	def test_cancel_transaction_clears_cart_without_changing_inventory(self):
		response = self.client.delete(f"/api/users/{self.user.pk}/cart/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(CartItem.objects.count(), 0)
		self.assertEqual(Sale.objects.count(), 0)
		self.item.refresh_from_db()
		self.assertEqual(self.item.item_quantity, 8)
