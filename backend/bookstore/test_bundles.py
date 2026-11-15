from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Category, CourseSupplyBundle, Item


class CourseSupplyBundleApiTests(APITestCase):
    def setUp(self):
        manager = get_user_model().objects.create_user(
            username="bundle-manager",
            password="manager-password",
            is_staff=True,
        )
        self.client.force_authenticate(user=manager)
        supplies = Category.objects.create(category_name="Course Supplies")
        apparel = Category.objects.create(category_name="Apparel")
        self.notebook = Item.objects.create(
            item="Notebook",
            item_quantity=8,
            item_price="4.00",
            category=supplies,
        )
        self.pencils = Item.objects.create(
            item="Pencils",
            item_quantity=5,
            item_price="2.00",
            category=supplies,
        )
        self.hoodie = Item.objects.create(
            item="Hoodie",
            item_quantity=2,
            item_price="20.00",
            category=apparel,
        )
        self.url = "/api/bundles/"

    def test_manager_can_create_list_update_and_delete_bundle(self):
        created = self.client.post(
            self.url,
            {
                "name": "ARTS 1311 Kit",
                "items": [self.notebook.pk, self.pencils.pk],
            },
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        bundle_id = created.data["id"]
        self.assertEqual(created.data["name"], "ARTS 1311 Kit")
        self.assertCountEqual(
            created.data["items"],
            [self.notebook.pk, self.pencils.pk],
        )

        listed = self.client.get(self.url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)

        updated = self.client.patch(
            f"{self.url}{bundle_id}/",
            {"items": [self.notebook.pk]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["items"], [self.notebook.pk])

        deleted = self.client.delete(f"{self.url}{bundle_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(CourseSupplyBundle.objects.filter(pk=bundle_id).exists())

    def test_bundle_list_is_public_and_mutations_require_manager(self):
        bundle = CourseSupplyBundle.objects.create(name="ARTS 1311 Kit")
        bundle.items.add(self.notebook)
        self.client.force_authenticate(user=None)

        listed = self.client.get(self.url)
        denied = self.client.post(
            self.url,
            {"name": "BIO 1406 Kit", "items": [self.pencils.pk]},
            format="json",
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(denied.status_code, 401)

    def test_student_can_load_bundle_and_add_each_item_to_their_cart(self):
        bundle = CourseSupplyBundle.objects.create(name="ARTS 1311 Kit")
        bundle.items.add(self.notebook, self.pencils)
        student = get_user_model().objects.create_user(
            username="bundle-student",
            password="student-password",
        )
        self.client.force_authenticate(user=student)

        listed = self.client.get(self.url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]["id"], bundle.pk)
        self.assertCountEqual(
            listed.data[0]["items"],
            [self.notebook.pk, self.pencils.pk],
        )

        added_items = []
        for item in (self.notebook, self.pencils):
            response = self.client.post(
                f"/api/users/{student.pk}/cart/items/",
                {"item": item.pk},
                format="json",
            )
            self.assertEqual(response.status_code, 201)
            added_items.append(response.data["item"])

        cart = self.client.get(f"/api/users/{student.pk}/cart/")
        self.assertEqual(cart.status_code, 200)
        self.assertCountEqual(
            [line["item"] for line in cart.data["cart_items"]],
            added_items,
        )

    def test_student_is_told_when_a_bundle_component_is_out_of_stock(self):
        self.notebook.item_quantity = 0
        self.notebook.save(update_fields=["item_quantity"])
        student = get_user_model().objects.create_user(
            username="bundle-stock-student",
            password="student-password",
        )
        self.client.force_authenticate(user=student)

        rejected = self.client.post(
            f"/api/users/{student.pk}/cart/items/",
            {"item": self.notebook.pk},
            format="json",
        )
        added = self.client.post(
            f"/api/users/{student.pk}/cart/items/",
            {"item": self.pencils.pk},
            format="json",
        )

        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(
            rejected.data["error"],
            "Requested quantity exceeds available inventory.",
        )
        self.assertEqual(added.status_code, 201)
        cart = self.client.get(f"/api/users/{student.pk}/cart/")
        self.assertEqual(
            [line["item"] for line in cart.data["cart_items"]],
            [self.pencils.pk],
        )

    def test_bundle_requires_items_and_rejects_duplicate_or_apparel_items(self):
        empty = self.client.post(
            self.url,
            {"name": "Empty Kit", "items": []},
            format="json",
        )
        duplicate = self.client.post(
            self.url,
            {
                "name": "Duplicate Kit",
                "items": [self.notebook.pk, self.notebook.pk],
            },
            format="json",
        )
        apparel = self.client.post(
            self.url,
            {"name": "Apparel Kit", "items": [self.hoodie.pk]},
            format="json",
        )

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(apparel.status_code, 400)
        self.assertEqual(CourseSupplyBundle.objects.count(), 0)

    def test_bundle_names_are_unique_without_case_sensitivity(self):
        self.client.post(
            self.url,
            {"name": "ARTS 1311 Kit", "items": [self.notebook.pk]},
            format="json",
        )

        duplicate = self.client.post(
            self.url,
            {"name": "arts 1311 kit", "items": [self.pencils.pk]},
            format="json",
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(CourseSupplyBundle.objects.count(), 1)

    def test_item_in_bundle_cannot_be_deleted_until_removed_from_bundle(self):
        bundle = CourseSupplyBundle.objects.create(name="ARTS 1311 Kit")
        bundle.items.add(self.notebook)

        denied = self.client.delete(f"/api/items/{self.notebook.pk}/")

        self.assertEqual(denied.status_code, 400)
        self.assertTrue(Item.objects.filter(pk=self.notebook.pk).exists())

        bundle.items.clear()
        allowed = self.client.delete(f"/api/items/{self.notebook.pk}/")

        self.assertEqual(allowed.status_code, 204)
        self.assertFalse(Item.objects.filter(pk=self.notebook.pk).exists())
