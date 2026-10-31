from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Cart, CartItem, Category, Item, Sale, SaleItem, StudentId


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

	def test_adding_item_to_cart_does_not_reduce_inventory(self):
		response = self.client.post(
			f"/api/users/{self.user.pk}/cart/items/",
			{"item": self.item.item_id, "quantity": 1},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.item.refresh_from_db()
		self.assertEqual(self.item.item_quantity, 8)
		self.assertEqual(CartItem.objects.get(item=self.item).quantity, 3)

	def test_sales_history_can_list_and_retrieve_completed_receipts(self):
		checkout_response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "30.00"},
			format="json",
		)
		receipt_number = checkout_response.data["receipt_number"]

		list_response = self.client.get("/api/sales/")
		detail_response = self.client.get(f"/api/sales/{receipt_number}/")

		self.assertEqual(list_response.status_code, 200)
		self.assertEqual(detail_response.status_code, 200)
		self.assertEqual(list_response.data[0]["receipt_number"], receipt_number)
		self.assertEqual(detail_response.data["receipt_number"], receipt_number)
		self.assertTrue(detail_response.data["issued_at"])
		self.assertEqual(detail_response.data["total"], "27.06")
		self.assertEqual(detail_response.data["items"][0]["item_name"], "Test Book")
		self.assertEqual(detail_response.data["items"][0]["quantity"], 2)

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


class DiscountApiTests(APITestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="discount-user",
			password="test-password",
		)
		category = Category.objects.create(category_name="Fiction")
		self.item = Item.objects.create(
			item="Test Book",
			item_quantity=8,
			item_price=Decimal("12.50"),
			item_code="BK-TEST",
			category=category,
		)
		cart = Cart.objects.create(user=self.user)
		self.cart_item = CartItem.objects.create(cart=cart, item=self.item, quantity=2)
		StudentId.objects.create(student_id="S1001")
		StudentId.objects.create(student_id="S2002", is_active=False)
		self.cart_url = f"/api/users/{self.user.pk}/cart/"
		self.checkout_url = f"/api/users/{self.user.pk}/checkout/"

	def checkout(self, **discount_fields):
		return self.client.post(
			self.checkout_url,
			{"payment_method": "card", **discount_fields},
			format="json",
		)

	def assert_no_sale_and_cart_intact(self):
		self.item.refresh_from_db()
		self.assertEqual(self.item.item_quantity, 8)
		self.assertFalse(Sale.objects.exists())
		self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

	def test_student_with_valid_id_gets_discount_taxed_on_discounted_price(self):
		response = self.checkout(role="Student", student_id="S1001")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["subtotal"], "25.00")
		self.assertEqual(response.data["discount_type"], "student")
		self.assertEqual(response.data["discount_percent"], "10.00")
		self.assertEqual(response.data["discount_amount"], "2.50")
		self.assertEqual(response.data["tax_amount"], "1.86")
		self.assertEqual(response.data["total"], "24.36")

	def test_invalid_or_inactive_student_id_is_rejected_without_changes(self):
		for student_id in ("NOPE", "S2002"):
			with self.subTest(student_id=student_id):
				response = self.checkout(role="Student", student_id=student_id)

				self.assertEqual(response.status_code, 400)
				self.assertEqual(response.data["error"], "Enter a valid student ID.")
				self.assert_no_sale_and_cart_intact()

				cart_response = self.client.get(
					self.cart_url,
					{"role": "Student", "student_id": student_id},
				)
				self.assertEqual(cart_response.status_code, 400)

	def test_student_with_blank_id_pays_full_price(self):
		response = self.checkout(role="Student", student_id="  ")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_type"], "")
		self.assertEqual(response.data["discount_amount"], "0.00")
		self.assertEqual(response.data["total"], "27.06")

	def test_manager_discount_follows_checkbox(self):
		cases = (
			({"use_employee_discount": "true"}, "employee", Decimal("5.00"), Decimal("21.65")),
			({"use_employee_discount": "false"}, "", Decimal("0.00"), Decimal("27.06")),
			({}, "", Decimal("0.00"), Decimal("27.06")),
		)
		for fields, discount_type, discount, total in cases:
			with self.subTest(fields=fields):
				response = self.client.get(self.cart_url, {"role": "Manager", **fields})

				self.assertEqual(response.data["discount_type"], discount_type)
				self.assertEqual(response.data["discount_amount"], discount)
				self.assertEqual(response.data["total_price"], total)

	def test_manager_checkout_with_json_boolean_checkbox(self):
		response = self.checkout(role="Manager", use_employee_discount=True)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_type"], "employee")
		self.assertEqual(response.data["total"], "21.65")

	def test_operator_is_discounted_automatically(self):
		response = self.checkout(role="Operator")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_type"], "employee")
		self.assertEqual(response.data["discount_percent"], "20.00")
		self.assertEqual(response.data["discount_amount"], "5.00")

	def test_no_role_gets_no_discount(self):
		response = self.checkout()

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_amount"], "0.00")

	def test_discount_applies_to_tax_exempt_items(self):
		self.item.tax_exempt = True
		self.item.save(update_fields=["tax_exempt"])

		response = self.checkout(role="Operator")

		self.assertEqual(response.data["discount_amount"], "5.00")
		self.assertEqual(response.data["tax_amount"], "0.00")
		self.assertEqual(response.data["total"], "20.00")

	def test_discount_rounds_to_cents_per_line(self):
		self.item.item_price = Decimal("9.99")
		self.item.save(update_fields=["item_price"])
		self.cart_item.quantity = 1
		self.cart_item.save(update_fields=["quantity"])

		response = self.checkout(role="Student", student_id="S1001")

		self.assertEqual(response.data["discount_amount"], "1.00")
		self.assertEqual(response.data["tax_amount"], "0.74")
		self.assertEqual(response.data["total"], "9.73")

	def test_cart_total_matches_charged_total(self):
		params = {"role": "Student", "student_id": "S1001"}
		cart_total = self.client.get(self.cart_url, params).data["total_price"]

		response = self.checkout(**params)

		self.assertEqual(Decimal(response.data["total"]), cart_total)

	def test_receipt_line_is_net_of_discount_and_stored(self):
		response = self.checkout(role="Student", student_id="S1001")

		sale = Sale.objects.get(receipt_number=response.data["receipt_number"])
		sale_item = sale.sale_items.get()
		self.assertEqual(sale.discount_type, "student")
		self.assertEqual(sale.discount_amount, Decimal("2.50"))
		self.assertEqual(sale_item.discount_amount, Decimal("2.50"))
		self.assertEqual(sale_item.line_total, Decimal("22.50"))
		self.assertEqual(response.data["items"][0]["discount_amount"], "2.50")
