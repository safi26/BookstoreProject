from django.db import models
from django.conf import settings
from django.db import models

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=200)

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

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
    )

    def __str__(self):
        return self.item

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

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "item"],
                name="unique_item_per_cart",
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
    item_name = models.CharField(max_length=200)
    item_code = models.CharField(max_length=30, blank=True, default="")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"