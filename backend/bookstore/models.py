from django.db import models
from django.conf import settings
from django.db.models import Q

class Category(models.Model):
    DISCOUNT_TYPES = [
        ("none", "No discount"),
        ("percent", "Percent off"),
        ("dollar", "Dollar off"),
    ]

    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=200)
    tax_exempt = models.BooleanField(default=False)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default="none")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.category_name

    class Meta:
        # Singular human-readable name
        verbose_name = "Category"
        # Plural human-readable name
        verbose_name_plural = "Categories"


class Item(models.Model):
    item = models.CharField(max_length=200)
    item_id = models.AutoField(primary_key=True)
    item_quantity = models.IntegerField()
    item_price = models.DecimalField(max_digits=5, decimal_places=2)
    author = models.CharField(max_length=200, blank=True, default="")
    item_code = models.CharField(max_length=30, blank=True, default="")
    isbn = models.CharField(max_length=13, blank=True, default="")
    badge = models.CharField(max_length=80, blank=True, default="")
    cover_url = models.URLField(blank=True, default="")
    tax_exempt = models.BooleanField(default=False)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
    )

    def __str__(self):
        return self.item

    @property
    def is_apparel(self):
        return self.category.category_name.casefold() == "apparel"


class ItemVariant(models.Model):
    SIZES = [
        ("XS", "XS"),
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("XXL", "XXL"),
        ("Unspecified", "Unspecified"),
    ]
    COLORS = [
        ("Blue", "Blue"),
        ("Green", "Green"),
        ("Black", "Black"),
        ("Grey", "Grey"),
        ("Red", "Red"),
        ("Unspecified", "Unspecified"),
    ]

    variant_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    size = models.CharField(max_length=20, choices=SIZES)
    color = models.CharField(max_length=20, choices=COLORS)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "size", "color"],
                name="unique_item_variant_size_color",
            )
        ]
        ordering = ["size", "color"]

    def __str__(self):
        return f"{self.item.item} — {self.size}, {self.color}"


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    variant = models.ForeignKey(
        ItemVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "item"],
                condition=Q(variant__isnull=True),
                name="unique_cart_item_without_variant",
            ),
            models.UniqueConstraint(
                fields=["cart", "item", "variant"],
                condition=Q(variant__isnull=False),
                name="unique_cart_item_variant",
            )
        ]

    def __str__(self):
        return f"{self.item.item} x {self.quantity}"


class Sale(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("card", "Card (demo)"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookstore_sales",
    )
    receipt_number = models.CharField(max_length=32, unique=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    cash_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    change_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.receipt_number


class SaleItem(models.Model):
    DISCOUNT_TYPES = [
        ("none", "No discount"),
        ("percent", "Percent off"),
        ("dollar", "Dollar off"),
    ]

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="sale_items",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_items",
    )
    variant_size = models.CharField(max_length=20, blank=True, default="")
    variant_color = models.CharField(max_length=40, blank=True, default="")
    item_name = models.CharField(max_length=200)
    item_code = models.CharField(max_length=30, blank=True, default="")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default="none")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"