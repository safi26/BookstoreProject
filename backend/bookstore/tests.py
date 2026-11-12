from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from .models import Cart, CartItem, Category, Item, Sale, SaleItem, StudentId


class CheckoutApiTests(APITestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="checkout-student",
			password="test-password",
		)
		self.client.force_authenticate(user=self.user)
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

	def test_percent_discount_is_applied_before_tax_and_saved_to_receipt(self):
		self.item.category.discount_type = "percent"
		self.item.category.discount_value = Decimal("10.00")
		self.item.category.save(update_fields=["discount_type", "discount_value"])
		response = self.client.post(
			self.url,
			{
				"payment_method": "cash",
				"cash_received": "24.36",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_total"], "2.50")
		self.assertEqual(response.data["subtotal"], "22.50")
		self.assertEqual(response.data["tax_amount"], "1.86")
		self.assertEqual(response.data["total"], "24.36")
		receipt_item = response.data["items"][0]
		self.assertEqual(receipt_item["discount_type"], "percent")
		self.assertEqual(receipt_item["discount_value"], "10.00")
		self.assertEqual(receipt_item["discount_amount"], "2.50")
		self.assertEqual(receipt_item["line_total"], "22.50")
		sale_item = SaleItem.objects.get()
		self.assertEqual(sale_item.discount_amount, Decimal("2.50"))
		self.assertEqual(sale_item.tax_amount, Decimal("1.86"))

	def test_student_cannot_submit_checkout_discounts(self):
		self.item.category.discount_type = "percent"
		self.item.category.discount_value = Decimal("20.00")
		self.item.category.save(update_fields=["discount_type", "discount_value"])
		cart_item = CartItem.objects.get(item=self.item)
		response = self.client.post(
			self.url,
			{
				"payment_method": "card",
				"discounts": [{
					"cart_item_id": cart_item.pk,
					"discount_type": "dollar",
					"discount_value": "25.00",
				}],
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Sale.objects.count(), 0)
		self.assertEqual(CartItem.objects.get().quantity, 2)

	def test_different_category_discounts_apply_to_their_own_items(self):
		second_category = Category.objects.create(
			category_name="Supplies",
			discount_type="dollar",
			discount_value=Decimal("2.00"),
		)
		second_item = Item.objects.create(
			item="Second Item",
			item_quantity=5,
			item_price=Decimal("10.00"),
			category=second_category,
		)
		cart = Cart.objects.get(user=self.user)
		CartItem.objects.create(cart=cart, item=second_item, quantity=1)
		self.item.category.discount_type = "percent"
		self.item.category.discount_value = Decimal("10.00")
		self.item.category.save(update_fields=["discount_type", "discount_value"])

		response = self.client.post(
			self.url,
			{"payment_method": "card"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_total"], "4.50")
		self.assertEqual(response.data["subtotal"], "30.50")
		receipt_items = {
			receipt_item["item_name"]: receipt_item
			for receipt_item in response.data["items"]
		}
		self.assertEqual(receipt_items["Test Book"]["discount_amount"], "2.50")
		self.assertEqual(receipt_items["Second Item"]["discount_amount"], "2.00")

	def test_dollar_discount_is_capped_at_line_total(self):
		self.item.category.discount_type = "dollar"
		self.item.category.discount_value = Decimal("30.00")
		self.item.category.save(update_fields=["discount_type", "discount_value"])
		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "0.00"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_total"], "25.00")
		self.assertEqual(response.data["subtotal"], "0.00")
		self.assertEqual(response.data["tax_amount"], "0.00")
		self.assertEqual(response.data["total"], "0.00")
		self.assertEqual(response.data["items"][0]["discount_amount"], "25.00")
		self.assertEqual(response.data["items"][0]["line_total"], "0.00")

	def test_dollar_discount_is_applied_before_tax(self):
		self.item.category.discount_type = "dollar"
		self.item.category.discount_value = Decimal("5.00")
		self.item.category.save(update_fields=["discount_type", "discount_value"])
		response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "21.65"},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_total"], "5.00")
		self.assertEqual(response.data["subtotal"], "20.00")
		self.assertEqual(response.data["tax_amount"], "1.65")
		self.assertEqual(response.data["total"], "21.65")
		self.assertEqual(response.data["items"][0]["line_total"], "20.00")

	def test_checkout_rejects_client_supplied_discounts(self):
		response = self.client.post(
			self.url,
			{
				"payment_method": "card",
				"discounts": [],
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Sale.objects.count(), 0)
		self.assertEqual(CartItem.objects.get().quantity, 2)

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

	def test_user_cannot_access_another_users_cart_or_checkout(self):
		other_user = get_user_model().objects.create_user(username="other-student")
		self.client.force_authenticate(user=other_user)

		cart_response = self.client.get(f"/api/users/{self.user.pk}/cart/")
		checkout_response = self.client.post(
			self.url,
			{"payment_method": "card"},
			format="json",
		)

		self.assertEqual(cart_response.status_code, 403)
		self.assertEqual(checkout_response.status_code, 403)

	def test_sales_history_can_list_and_retrieve_completed_receipts(self):
		checkout_response = self.client.post(
			self.url,
			{"payment_method": "cash", "cash_received": "30.00"},
			format="json",
		)
		receipt_number = checkout_response.data["receipt_number"]

		manager = get_user_model().objects.create_user(
			username="sales-history-manager",
			password="test-manager-password",
			is_staff=True,
		)
		self.client.force_authenticate(user=manager)
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
		self.client.force_authenticate(user=self.user)
		self.category = Category.objects.create(category_name="Fiction")
		self.item = Item.objects.create(
			item="Test Book",
			item_quantity=8,
			item_price=Decimal("12.50"),
			item_code="BK-TEST",
			category=self.category,
		)
		cart = Cart.objects.create(user=self.user)
		self.cart_item = CartItem.objects.create(cart=cart, item=self.item, quantity=2)
		StudentId.objects.create(student_id="S1001")
		StudentId.objects.create(student_id="S2002", is_active=False)
		self.cart_url = f"/api/users/{self.user.pk}/cart/"
		self.checkout_url = f"/api/users/{self.user.pk}/checkout/"

	def join_group(self, name):
		group, _ = Group.objects.get_or_create(name=name)
		self.user.groups.add(group)

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
		response = self.checkout(student_id="S1001")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["subtotal"], "25.00")
		self.assertEqual(response.data["customer_discount_type"], "student")
		self.assertEqual(response.data["customer_discount_percent"], "10.00")
		self.assertEqual(response.data["customer_discount_amount"], "2.50")
		self.assertEqual(response.data["tax_amount"], "1.86")
		self.assertEqual(response.data["total"], "24.36")

	def test_invalid_or_inactive_student_id_is_rejected_without_changes(self):
		for student_id in ("NOPE", "S2002"):
			with self.subTest(student_id=student_id):
				response = self.checkout(student_id=student_id)

				self.assertEqual(response.status_code, 400)
				self.assertEqual(response.data["error"], "Enter a valid student ID.")
				self.assert_no_sale_and_cart_intact()

				cart_response = self.client.get(self.cart_url, {"student_id": student_id})
				self.assertEqual(cart_response.status_code, 400)

	def test_student_with_blank_id_pays_full_price(self):
		response = self.checkout(student_id="  ")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["customer_discount_type"], "")
		self.assertEqual(response.data["customer_discount_amount"], "0.00")
		self.assertEqual(response.data["total"], "27.06")

	def test_student_cannot_claim_employee_discount(self):
		response = self.checkout(role="Manager", use_employee_discount=True)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["customer_discount_type"], "")
		self.assertEqual(response.data["total"], "27.06")

	def test_manager_discount_follows_checkbox(self):
		self.join_group("Manager")
		cases = (
			({"use_employee_discount": "true"}, "employee", Decimal("5.00"), Decimal("21.65")),
			({"use_employee_discount": "false"}, "", Decimal("0.00"), Decimal("27.06")),
			({}, "", Decimal("0.00"), Decimal("27.06")),
		)
		for fields, discount_type, discount, total in cases:
			with self.subTest(fields=fields):
				response = self.client.get(self.cart_url, fields)

				self.assertEqual(response.data["customer_discount_type"], discount_type)
				self.assertEqual(response.data["customer_discount_amount"], discount)
				self.assertEqual(response.data["total_price"], total)

	def test_manager_checkout_with_json_boolean_checkbox(self):
		self.join_group("Manager")
		response = self.checkout(use_employee_discount=True)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["customer_discount_type"], "employee")
		self.assertEqual(response.data["total"], "21.65")

	def test_operator_is_discounted_automatically(self):
		self.join_group("Operator")
		response = self.checkout()

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["customer_discount_type"], "employee")
		self.assertEqual(response.data["customer_discount_percent"], "20.00")
		self.assertEqual(response.data["customer_discount_amount"], "5.00")

	def test_no_student_id_gets_no_discount(self):
		response = self.checkout()

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["customer_discount_amount"], "0.00")

	def test_discount_applies_to_tax_exempt_items(self):
		self.item.tax_exempt = True
		self.item.save(update_fields=["tax_exempt"])
		self.join_group("Operator")

		response = self.checkout()

		self.assertEqual(response.data["customer_discount_amount"], "5.00")
		self.assertEqual(response.data["tax_amount"], "0.00")
		self.assertEqual(response.data["total"], "20.00")

	def test_discount_rounds_to_cents_per_line(self):
		self.item.item_price = Decimal("9.99")
		self.item.save(update_fields=["item_price"])
		self.cart_item.quantity = 1
		self.cart_item.save(update_fields=["quantity"])

		response = self.checkout(student_id="S1001")

		self.assertEqual(response.data["customer_discount_amount"], "1.00")
		self.assertEqual(response.data["tax_amount"], "0.74")
		self.assertEqual(response.data["total"], "9.73")

	def test_customer_discount_stacks_after_category_discount(self):
		self.category.discount_type = "dollar"
		self.category.discount_value = Decimal("5.00")
		self.category.save(update_fields=["discount_type", "discount_value"])

		response = self.checkout(student_id="S1001")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["discount_total"], "5.00")
		self.assertEqual(response.data["subtotal"], "20.00")
		self.assertEqual(response.data["customer_discount_amount"], "2.00")
		self.assertEqual(response.data["tax_amount"], "1.49")
		self.assertEqual(response.data["total"], "19.49")
		receipt_item = response.data["items"][0]
		self.assertEqual(receipt_item["discount_amount"], "5.00")
		self.assertEqual(receipt_item["customer_discount_amount"], "2.00")
		self.assertEqual(receipt_item["line_total"], "18.00")

	def test_student_discount_skips_exempt_items(self):
		other = Item.objects.create(
			item="Exempt Item",
			item_quantity=5,
			item_price=Decimal("10.00"),
			category=self.category,
			student_discount_exempt=True,
		)
		CartItem.objects.create(cart=self.cart_item.cart, item=other, quantity=1)

		response = self.checkout(student_id="S1001")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["customer_discount_type"], "student")
		self.assertEqual(response.data["customer_discount_amount"], "2.50")
		receipt_items = {line["item_name"]: line for line in response.data["items"]}
		self.assertEqual(receipt_items["Exempt Item"]["customer_discount_amount"], "0.00")
		self.assertEqual(receipt_items["Test Book"]["customer_discount_amount"], "2.50")

	def test_valid_student_id_with_only_exempt_items_reports_zero_discount(self):
		self.item.student_discount_exempt = True
		self.item.save(update_fields=["student_discount_exempt"])

		response = self.client.get(self.cart_url, {"student_id": "S1001"})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["customer_discount_type"], "student")
		self.assertEqual(response.data["customer_discount_amount"], 0)

	def test_student_discount_skips_items_in_exempt_category(self):
		self.category.student_discount_exempt = True
		self.category.save(update_fields=["student_discount_exempt"])

		response = self.checkout(student_id="S1001")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["customer_discount_type"], "student")
		self.assertEqual(response.data["customer_discount_amount"], "0.00")
		self.assertEqual(response.data["total"], "27.06")

	def test_category_student_exemption_toggle_updates_each_item(self):
		second = Item.objects.create(
			item="Second Book", item_quantity=3, item_price=Decimal("5.00"), category=self.category
		)
		other_category = Category.objects.create(category_name="Snacks")
		outside = Item.objects.create(
			item="Outside Item", item_quantity=3, item_price=Decimal("2.00"), category=other_category
		)
		self.join_group("Manager")
		url = f"/api/categories/{self.category.pk}/"

		response = self.client.patch(url, {"student_discount_exempt": True}, format="json")

		self.assertEqual(response.status_code, 200)
		for item in (self.item, second, outside):
			item.refresh_from_db()
		self.assertTrue(self.item.student_discount_exempt)
		self.assertTrue(second.student_discount_exempt)
		self.assertFalse(outside.student_discount_exempt)

		response = self.client.patch(url, {"student_discount_exempt": False}, format="json")

		self.assertEqual(response.status_code, 200)
		self.item.refresh_from_db()
		second.refresh_from_db()
		self.assertFalse(self.item.student_discount_exempt)
		self.assertFalse(second.student_discount_exempt)

	def test_category_tax_exemption_toggle_updates_each_item(self):
		second = Item.objects.create(
			item="Second Book", item_quantity=3, item_price=Decimal("5.00"), category=self.category
		)
		other_category = Category.objects.create(category_name="Snacks")
		outside = Item.objects.create(
			item="Outside Item", item_quantity=3, item_price=Decimal("2.00"), category=other_category
		)
		self.join_group("Manager")
		url = f"/api/categories/{self.category.pk}/"

		response = self.client.patch(url, {"tax_exempt": True}, format="json")

		self.assertEqual(response.status_code, 200)
		for item in (self.item, second, outside):
			item.refresh_from_db()
		self.assertTrue(self.item.tax_exempt)
		self.assertTrue(second.tax_exempt)
		self.assertFalse(outside.tax_exempt)
		# Only the toggled flag cascades.
		self.assertFalse(self.item.student_discount_exempt)

		response = self.client.patch(url, {"tax_exempt": False}, format="json")

		self.assertEqual(response.status_code, 200)
		self.item.refresh_from_db()
		second.refresh_from_db()
		self.assertFalse(self.item.tax_exempt)
		self.assertFalse(second.tax_exempt)

	def test_category_tax_exemption_removes_tax_at_checkout(self):
		self.join_group("Manager")
		self.client.patch(
			f"/api/categories/{self.category.pk}/", {"tax_exempt": True}, format="json"
		)
		self.user.groups.clear()

		response = self.checkout()

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["tax_amount"], "0.00")
		self.assertEqual(response.data["total"], "25.00")

	def test_item_exemption_takes_priority_over_category_toggle(self):
		self.join_group("Manager")
		category_url = f"/api/categories/{self.category.pk}/"
		for field in ("tax_exempt", "student_discount_exempt"):
			with self.subTest(field=field):
				other = Item.objects.create(
					item=f"Other {field}", item_quantity=1, item_price=Decimal("1.00"), category=self.category
				)
				# Same order the dashboard uses: the item's own change saves before the category's.
				self.client.patch(f"/api/items/{self.item.pk}/", {field: True}, format="json")
				self.client.patch(category_url, {field: True}, format="json")
				self.item.refresh_from_db()
				other.refresh_from_db()
				self.assertTrue(getattr(self.item, field))
				self.assertFalse(getattr(self.item, f"{field}_from_category"))
				self.assertTrue(getattr(other, field))
				self.assertTrue(getattr(other, f"{field}_from_category"))

				self.client.patch(category_url, {field: False}, format="json")

				self.item.refresh_from_db()
				other.refresh_from_db()
				self.assertTrue(getattr(self.item, field), "item's own mark was cleared by the category")
				self.assertFalse(getattr(other, field))

	def test_category_toggle_does_not_overwrite_item_marked_while_category_was_on(self):
		self.join_group("Manager")
		category_url = f"/api/categories/{self.category.pk}/"
		for field in ("tax_exempt", "student_discount_exempt"):
			with self.subTest(field=field):
				self.client.patch(category_url, {field: True}, format="json")
				# Unchecking the category and checking the item in one save.
				self.client.patch(f"/api/items/{self.item.pk}/", {field: True}, format="json")
				self.client.patch(category_url, {field: False}, format="json")

				self.item.refresh_from_db()
				self.assertTrue(getattr(self.item, field))
				self.assertFalse(getattr(self.item, f"{field}_from_category"))

	def test_item_edit_without_exemption_fields_keeps_category_mark(self):
		self.join_group("Manager")
		category_url = f"/api/categories/{self.category.pk}/"
		self.client.patch(category_url, {"tax_exempt": True}, format="json")

		response = self.client.patch(
			f"/api/items/{self.item.pk}/", {"item_price": "13.00"}, format="json"
		)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data["tax_exempt_from_category"])

		self.client.patch(category_url, {"tax_exempt": False}, format="json")
		self.item.refresh_from_db()
		self.assertFalse(self.item.tax_exempt)

	def test_moving_item_between_categories_follows_category_exemption(self):
		exempt = Category.objects.create(category_name="Textbooks", tax_exempt=True)
		self.join_group("Manager")
		item_url = f"/api/items/{self.item.pk}/"

		self.client.patch(item_url, {"category": exempt.pk}, format="json")
		self.item.refresh_from_db()
		self.assertTrue(self.item.tax_exempt)
		self.assertTrue(self.item.tax_exempt_from_category)

		self.client.patch(item_url, {"category": self.category.pk}, format="json")
		self.item.refresh_from_db()
		self.assertFalse(self.item.tax_exempt)

	def test_unrelated_category_edit_keeps_item_exemptions(self):
		self.item.tax_exempt = True
		self.item.student_discount_exempt = True
		self.item.save(update_fields=["tax_exempt", "student_discount_exempt"])
		self.join_group("Manager")

		response = self.client.patch(
			f"/api/categories/{self.category.pk}/", {"category_name": "Novels"}, format="json"
		)

		self.assertEqual(response.status_code, 200)
		self.item.refresh_from_db()
		self.assertTrue(self.item.tax_exempt)
		self.assertTrue(self.item.student_discount_exempt)

	def test_student_exemption_does_not_block_employee_discount(self):
		self.item.student_discount_exempt = True
		self.item.save(update_fields=["student_discount_exempt"])
		self.join_group("Operator")

		response = self.checkout()

		self.assertEqual(response.data["customer_discount_type"], "employee")
		self.assertEqual(response.data["customer_discount_amount"], "5.00")

	def test_cart_total_matches_charged_total(self):
		self.category.discount_type = "percent"
		self.category.discount_value = Decimal("15.00")
		self.category.save(update_fields=["discount_type", "discount_value"])
		params = {"student_id": "S1001"}
		cart_total = self.client.get(self.cart_url, params).data["total_price"]

		response = self.checkout(**params)

		self.assertEqual(Decimal(response.data["total"]), cart_total)

	def test_receipt_line_is_net_of_discount_and_stored(self):
		response = self.checkout(student_id="S1001")

		sale = Sale.objects.get(receipt_number=response.data["receipt_number"])
		sale_item = sale.sale_items.get()
		self.assertEqual(sale.customer_discount_type, "student")
		self.assertEqual(sale.customer_discount_amount, Decimal("2.50"))
		self.assertEqual(sale_item.customer_discount_amount, Decimal("2.50"))
		self.assertEqual(sale_item.line_total, Decimal("22.50"))
		self.assertEqual(response.data["items"][0]["customer_discount_amount"], "2.50")

	def test_login_reports_operator_role(self):
		self.join_group("Operator")
		self.client.force_authenticate(user=None)

		response = self.client.post(
			"/api/auth/login/",
			{"user_id": self.user.pk, "password": "test-password"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["role"], "Operator")
