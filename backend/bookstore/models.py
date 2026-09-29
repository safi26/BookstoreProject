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