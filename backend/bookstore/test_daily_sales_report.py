from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Category, Item, Sale, SaleItem


class DailySalesReportApiTests(APITestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username="daily-report-manager",
            password="test-password",
            is_staff=True,
        )
        category = Category.objects.create(category_name="Books")
        item = Item.objects.create(
            item="Report Book",
            item_quantity=10,
            item_price=Decimal("10.00"),
            category=category,
        )
        sale = Sale.objects.create(
            user=self.manager,
            receipt_number="REPORT-001",
            payment_method="cash",
            subtotal=Decimal("20.00"),
            tax_amount=Decimal("1.65"),
            total=Decimal("21.65"),
            cash_received=Decimal("25.00"),
            change_due=Decimal("3.35"),
        )
        SaleItem.objects.create(
            sale=sale,
            item=item,
            item_name=item.item,
            quantity=2,
            unit_price=Decimal("10.00"),
            line_total=Decimal("20.00"),
            tax_amount=Decimal("1.65"),
        )

    def test_manager_receives_daily_totals_and_category_breakdown(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/reports/daily-sales/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_money_taken_in"], "21.65")
        self.assertEqual(response.data["sales_count"], 1)
        self.assertEqual(response.data["category_breakdown"], [
            {"category": "Books", "total": "21.65"},
        ])
        self.assertEqual(len(response.data["receipts"]), 1)
        self.assertEqual(response.data["receipts"][0]["receipt_number"], "REPORT-001")
        self.assertEqual(response.data["receipts"][0]["items"][0]["quantity"], 2)

    def test_non_manager_cannot_view_daily_report(self):
        shopper = get_user_model().objects.create_user(
            username="daily-report-shopper",
            password="test-password",
        )
        self.client.force_authenticate(user=shopper)

        response = self.client.get("/api/reports/daily-sales/")

        self.assertEqual(response.status_code, 403)

    def test_manager_can_request_a_specific_date(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/reports/daily-sales/", {"date": "2000-01-02"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["date"], "2000-01-02")
        self.assertEqual(response.data["total_money_taken_in"], "0.00")
        self.assertEqual(response.data["sales_count"], 0)
        self.assertEqual(response.data["receipts"], [])

    def test_invalid_report_date_is_rejected(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/reports/daily-sales/", {"date": "not-a-date"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.data)


class BestSellingItemsReportApiTests(APITestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username="best-sellers-manager",
            password="test-password",
            is_staff=True,
        )
        category = Category.objects.create(category_name="Books")
        self.book = Item.objects.create(
            item="Most Popular",
            item_quantity=10,
            item_price=Decimal("10.00"),
            item_code="BK-1",
            category=category,
        )
        self.other_book = Item.objects.create(
            item="Runner Up",
            item_quantity=10,
            item_price=Decimal("8.00"),
            item_code="BK-2",
            category=category,
        )
        self.sale = Sale.objects.create(
            user=self.manager,
            receipt_number="BEST-001",
            payment_method="cash",
            subtotal=Decimal("46.00"),
            total=Decimal("49.80"),
            cash_received=Decimal("50.00"),
            change_due=Decimal("0.20"),
        )
        SaleItem.objects.create(
            sale=self.sale,
            item=self.book,
            item_name="Most Popular",
            item_code="BK-1",
            quantity=3,
            unit_price=Decimal("10.00"),
            line_total=Decimal("30.00"),
        )
        SaleItem.objects.create(
            sale=self.sale,
            item=self.book,
            item_name="Most Popular",
            item_code="BK-1",
            variant_size="M",
            variant_color="Blue",
            quantity=1,
            unit_price=Decimal("10.00"),
            line_total=Decimal("10.00"),
        )
        SaleItem.objects.create(
            sale=self.sale,
            item=self.other_book,
            item_name="Runner Up",
            item_code="BK-2",
            quantity=2,
            unit_price=Decimal("8.00"),
            line_total=Decimal("16.00"),
        )

    def test_manager_gets_items_ranked_by_quantity_with_inclusive_dates(self):
        self.client.force_authenticate(user=self.manager)
        report_date = self.sale.created_at.date().isoformat()

        response = self.client.get(
            "/api/reports/best-selling-items/",
            {"start_date": report_date, "end_date": report_date},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["start_date"], report_date)
        self.assertEqual(response.data["end_date"], report_date)
        self.assertEqual(response.data["items"], [
            {"item_name": "Most Popular", "item_code": "BK-1", "quantity_sold": 4},
            {"item_name": "Runner Up", "item_code": "BK-2", "quantity_sold": 2},
        ])

    def test_non_manager_cannot_view_best_selling_items(self):
        shopper = get_user_model().objects.create_user(
            username="best-sellers-shopper",
            password="test-password",
        )
        self.client.force_authenticate(user=shopper)

        response = self.client.get("/api/reports/best-selling-items/")

        self.assertEqual(response.status_code, 403)

    def test_invalid_and_reversed_date_ranges_are_rejected(self):
        self.client.force_authenticate(user=self.manager)

        invalid_response = self.client.get(
            "/api/reports/best-selling-items/",
            {"start_date": "bad", "end_date": "2026-11-15"},
        )
        reversed_response = self.client.get(
            "/api/reports/best-selling-items/",
            {"start_date": "2026-11-16", "end_date": "2026-11-15"},
        )

        self.assertEqual(invalid_response.status_code, 400)
        self.assertIn("start_date", invalid_response.data)
        self.assertEqual(reversed_response.status_code, 400)
        self.assertIn("end_date", reversed_response.data)
