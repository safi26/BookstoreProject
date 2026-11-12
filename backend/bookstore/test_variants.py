from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import CartItem, Category, Item, ItemVariant, SaleItem


class ApparelVariantApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username="variant-manager",
            password="manager-password",
            is_staff=True,
        )
        self.student = user_model.objects.create_user(
            username="variant-student",
            password="student-password",
        )
        self.category, _ = Category.objects.get_or_create(
            category_name="Apparel",
        )
        self.item = Item.objects.create(
            item="Navy Hoodie",
            item_quantity=0,
            item_price="20.00",
            item_code="HOODIE-NAVY",
            category=self.category,
        )
        self.variants_url = f"/api/items/{self.item.pk}/variants/"

    def create_variant(self, size, color, quantity):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            self.variants_url,
            {"size": size, "color": color, "quantity": quantity},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.data

    def test_manager_can_create_and_update_separate_size_color_stock(self):
        medium = self.create_variant("M", "Blue", 4)
        large = self.create_variant("L", "Blue", 3)

        self.assertNotEqual(medium["variant_id"], large["variant_id"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_quantity, 7)

        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f"{self.variants_url}{medium['variant_id']}/",
            {"quantity": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_quantity, 8)
        self.assertEqual(
            ItemVariant.objects.get(pk=medium["variant_id"]).quantity,
            5,
        )

    def test_manager_cannot_duplicate_a_size_and_color_combination(self):
        self.create_variant("M", "Blue", 4)
        self.client.force_authenticate(user=self.manager)

        duplicate = self.client.post(
            self.variants_url,
            {"size": "M", "color": "Blue", "quantity": 3},
            format="json",
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(ItemVariant.objects.filter(item=self.item).count(), 1)

    def test_variant_color_must_be_one_of_the_supported_colors(self):
        self.client.force_authenticate(user=self.manager)

        invalid = self.client.post(
            self.variants_url,
            {"size": "M", "color": "Purple", "quantity": 3},
            format="json",
        )
        valid = self.client.post(
            self.variants_url,
            {"size": "M", "color": "Blue", "quantity": 3},
            format="json",
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(valid.data["color"], "Blue")

    def test_shopper_must_select_variant_and_cart_keeps_combinations_separate(self):
        medium = self.create_variant("M", "Blue", 4)
        large = self.create_variant("L", "Blue", 3)
        self.client.force_authenticate(user=self.student)

        missing_variant = self.client.post(
            f"/api/users/{self.student.pk}/cart/items/",
            {"item": self.item.pk, "quantity": 1},
            format="json",
        )
        medium_added = self.client.post(
            f"/api/users/{self.student.pk}/cart/items/",
            {
                "item": self.item.pk,
                "variant_id": medium["variant_id"],
                "quantity": 1,
            },
            format="json",
        )
        large_added = self.client.post(
            f"/api/users/{self.student.pk}/cart/items/",
            {
                "item": self.item.pk,
                "variant_id": large["variant_id"],
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(missing_variant.status_code, 400)
        self.assertEqual(medium_added.status_code, 201)
        self.assertEqual(large_added.status_code, 201)
        self.assertEqual(CartItem.objects.filter(cart__user=self.student).count(), 2)
        cart = self.client.get(f"/api/users/{self.student.pk}/cart/")
        self.assertEqual(
            {
                (line["variant_size"], line["variant_color"], line["quantity"])
                for line in cart.data["cart_items"]
            },
            {("M", "Blue", 1), ("L", "Blue", 1)},
        )

    def test_checkout_decrements_each_variant_and_snapshots_it_on_receipt(self):
        medium = self.create_variant("M", "Blue", 4)
        large = self.create_variant("L", "Blue", 3)
        self.client.force_authenticate(user=self.student)
        cart_url = f"/api/users/{self.student.pk}/cart/items/"
        for variant in (medium, large):
            self.client.post(
                cart_url,
                {
                    "item": self.item.pk,
                    "variant_id": variant["variant_id"],
                    "quantity": 1,
                },
                format="json",
            )

        response = self.client.post(
            f"/api/users/{self.student.pk}/checkout/",
            {"payment_method": "card"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            {(line["variant_size"], line["variant_color"]) for line in response.data["items"]},
            {("M", "Blue"), ("L", "Blue")},
        )
        self.assertEqual(
            set(
                SaleItem.objects.filter(sale__user=self.student).values_list(
                    "variant_size",
                    "variant_color",
                )
            ),
            {("M", "Blue"), ("L", "Blue")},
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_quantity, 5)
        self.assertEqual(
            ItemVariant.objects.get(pk=medium["variant_id"]).quantity,
            3,
        )
        self.assertEqual(
            ItemVariant.objects.get(pk=large["variant_id"]).quantity,
            2,
        )

    def test_add_and_checkout_cannot_exceed_selected_variant_stock(self):
        medium = self.create_variant("M", "Blue", 2)
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f"/api/users/{self.student.pk}/cart/items/",
            {
                "item": self.item.pk,
                "variant_id": medium["variant_id"],
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(CartItem.objects.filter(cart__user=self.student).exists())
        self.assertEqual(
            ItemVariant.objects.get(pk=medium["variant_id"]).quantity,
            2,
        )

    def test_checkout_rejects_cart_quantity_above_variant_stock(self):
        medium = self.create_variant("M", "Blue", 2)
        self.client.force_authenticate(user=self.student)
        self.client.post(
            f"/api/users/{self.student.pk}/cart/items/",
            {
                "item": self.item.pk,
                "variant_id": medium["variant_id"],
                "quantity": 1,
            },
            format="json",
        )
        cart_item = CartItem.objects.get(cart__user=self.student)
        cart_item.quantity = 3
        cart_item.save(update_fields=["quantity"])

        response = self.client.post(
            f"/api/users/{self.student.pk}/checkout/",
            {"payment_method": "card"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ItemVariant.objects.get(pk=medium["variant_id"]).quantity, 2)
        self.assertFalse(SaleItem.objects.filter(sale__user=self.student).exists())

    def test_students_cannot_manage_variants_and_non_apparel_cannot_have_them(self):
        self.client.force_authenticate(user=self.student)
        denied = self.client.post(
            self.variants_url,
            {"size": "M", "color": "Blue", "quantity": 2},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        supplies = Category.objects.create(category_name="Variant test supplies")
        non_apparel = Item.objects.create(
            item="Binder",
            item_quantity=2,
            item_price="5.00",
            category=supplies,
        )
        self.client.force_authenticate(user=self.manager)
        invalid = self.client.post(
            f"/api/items/{non_apparel.pk}/variants/",
            {"size": "M", "color": "Blue", "quantity": 2},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

    def test_legacy_apparel_stock_is_created_as_unspecified_variant(self):
        legacy_item = Item.objects.get(item="Campus Hoodie")
        legacy_variant = legacy_item.variants.get(
            size="Unspecified",
            color="Unspecified",
        )
        self.assertEqual(legacy_variant.quantity, legacy_item.item_quantity)

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            "/api/items/",
            {
                "item": "Legacy Hoodie",
                "item_quantity": 6,
                "item_price": "24.00",
                "category": self.category.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["variants"],
            [{
                "variant_id": response.data["variants"][0]["variant_id"],
                "size": "Unspecified",
                "color": "Unspecified",
                "quantity": 6,
            }],
        )
