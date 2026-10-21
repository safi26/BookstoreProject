from rest_framework.test import APITestCase

from .models import Category, Item


class StoreCategoryDefaultsApiTests(APITestCase):
    def test_default_store_categories_are_available(self):
        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [category["category_name"] for category in response.data],
            sorted([
                "Snacks",
                "Drinks",
                "Stationery",
                "Exam Supplies",
                "Art Supplies",
                "Apparel",
                "Course Supplies",
                "Books",
            ]),
        )

    def test_category_tax_exemption_can_be_toggled_through_api(self):
        category = Category.objects.create(category_name="Exemption test")

        enabled = self.client.patch(
            f"/api/categories/{category.category_id}/",
            {"tax_exempt": True},
            format="json",
        )
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.data["tax_exempt"])

        disabled = self.client.patch(
            f"/api/categories/{category.category_id}/",
            {"tax_exempt": False},
            format="json",
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.data["tax_exempt"])

    def test_category_can_be_created_through_api(self):
        response = self.client.post(
            "/api/categories/",
            {"category_name": "New category"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["category_name"], "New category")
        self.assertFalse(response.data["tax_exempt"])
        self.assertTrue(Category.objects.filter(category_name="New category").exists())

    def test_empty_category_can_be_deleted_through_api(self):
        category = Category.objects.create(category_name="Delete test")

        response = self.client.delete(f"/api/categories/{category.category_id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Category.objects.filter(category_id=category.category_id).exists())

    def test_category_with_items_cannot_be_deleted(self):
        category = Category.objects.create(category_name="In use")
        item = Item.objects.create(
            item="Category item",
            item_quantity=2,
            item_price="5.00",
            category=category,
        )

        response = self.client.delete(f"/api/categories/{category.category_id}/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Move or remove", response.data["detail"])
        self.assertTrue(Category.objects.filter(category_id=category.category_id).exists())
        self.assertTrue(Item.objects.filter(item_id=item.item_id).exists())

    def test_item_tax_exemption_can_be_toggled_through_api(self):
        category = Category.objects.create(category_name="Exemption test")
        item = Item.objects.create(
            item="Tax test item",
            item_quantity=4,
            item_price="10.00",
            category=category,
        )

        enabled = self.client.patch(
            f"/api/items/{item.item_id}/",
            {"tax_exempt": True},
            format="json",
        )
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.data["tax_exempt"])

        disabled = self.client.patch(
            f"/api/items/{item.item_id}/",
            {"tax_exempt": False},
            format="json",
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.data["tax_exempt"])
