from django.db import models, transaction
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
    student_discount_exempt = models.BooleanField(default=False)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default="none")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.category_name

    # Exemption flags that, when toggled on a category, are written to the items in it.
    CASCADED_EXEMPTIONS = ("tax_exempt", "student_discount_exempt")

    def save(self, *args, **kwargs):
        previous = None
        if self.pk is not None:
            previous = (
                Category.objects.filter(pk=self.pk)
                .values(*self.CASCADED_EXEMPTIONS)
                .first()
            )
        with transaction.atomic():
            super().save(*args, **kwargs)
            if previous is None:
                return
            for field in self.CASCADED_EXEMPTIONS:
                if previous[field] == getattr(self, field):
                    continue
                source = f"{field}_from_category"
                # Items marked individually take priority: turning the category on leaves
                # already-exempt items alone, and turning it off only clears what it set.
                if getattr(self, field):
                    self.items.filter(**{field: False}).update(**{field: True, source: True})
                else:
                    self.items.filter(**{source: True}).update(**{field: False, source: False})

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
    student_discount_exempt = models.BooleanField(default=False)
    # True when the matching flag above was set by the category rather than on the item itself.
    tax_exempt_from_category = models.BooleanField(default=False)
    student_discount_exempt_from_category = models.BooleanField(default=False)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
    )

    def __str__(self):
        return self.item

    def save(self, *args, **kwargs):
        previous = None
        if self.pk is not None:
            previous = (
                Item.objects.filter(pk=self.pk)
                .values("category_id", *Category.CASCADED_EXEMPTIONS)
                .first()
            )
        category_changed = previous is None or previous["category_id"] != self.category_id
        for field in Category.CASCADED_EXEMPTIONS:
            source = f"{field}_from_category"
            if previous is not None and previous[field] != getattr(self, field):
                # Changed directly on the item, so it now belongs to the item.
                setattr(self, source, False)
            if category_changed:
                if getattr(self, source) and not getattr(self.category, field):
                    setattr(self, field, False)
                    setattr(self, source, False)
                elif getattr(self.category, field) and not getattr(self, field):
                    setattr(self, field, True)
                    setattr(self, source, True)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {
                *kwargs["update_fields"],
                *Category.CASCADED_EXEMPTIONS,
                *(f"{field}_from_category" for field in Category.CASCADED_EXEMPTIONS),
            }
        super().save(*args, **kwargs)

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


class StudentId(models.Model):
    student_id = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.student_id

    class Meta:
        verbose_name = "Student ID"
        verbose_name_plural = "Student IDs"


class Sale(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("card", "Card (demo)"),
    ]
    CUSTOMER_DISCOUNT_TYPES = [
        ("student", "Student"),
        ("employee", "Employee"),
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
    customer_discount_type = models.CharField(
        max_length=10,
        choices=CUSTOMER_DISCOUNT_TYPES,
        blank=True,
        default="",
    )
    customer_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    customer_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
    customer_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"