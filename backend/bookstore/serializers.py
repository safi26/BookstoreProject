from decimal import Decimal

from rest_framework import serializers

from .models import Category, Item, ItemVariant, Cart, CartItem, Sale, SaleItem
from .pricing import customer_discount_percent, price_line


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "category_id",
            "category_name",
            "tax_exempt",
            "student_discount_exempt",
            "discount_type",
            "discount_value",
        ]

    def validate(self, attrs):
        discount_type = attrs.get(
            "discount_type",
            getattr(self.instance, "discount_type", "none"),
        )
        discount_value = attrs.get(
            "discount_value",
            getattr(self.instance, "discount_value", Decimal("0.00")),
        )
        if discount_value < 0:
            raise serializers.ValidationError({
                "discount_value": "Discount values cannot be negative."
            })
        if discount_type == "percent" and discount_value > 100:
            raise serializers.ValidationError({
                "discount_value": "Percent discounts cannot exceed 100%."
            })
        return attrs


class ItemVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVariant
        fields = ["variant_id", "size", "color", "quantity"]
        read_only_fields = ["variant_id"]

    def validate_color(self, value):
        color = value.strip()
        supported_colors = {choice[0] for choice in ItemVariant.COLORS}
        supported_colors.discard("Unspecified")
        is_existing_legacy_color = (
            color == "Unspecified"
            and self.instance is not None
            and self.instance.color == color
        )
        if color not in supported_colors and not is_existing_legacy_color:
            raise serializers.ValidationError("Select a supported color.")
        return color

    def validate(self, attrs):
        size = attrs.get("size", getattr(self.instance, "size", None))
        color = attrs.get("color", getattr(self.instance, "color", None))
        item = self.instance.item if self.instance else self.context.get("item")
        if item and size and color:
            matching_variants = ItemVariant.objects.filter(
                item=item,
                size=size,
                color__iexact=color,
            )
            if self.instance:
                matching_variants = matching_variants.exclude(pk=self.instance.pk)
            if matching_variants.exists():
                raise serializers.ValidationError({
                    "color": "This size and color combination already exists."
                })
        return attrs


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.category_name",
        read_only=True,
    )
    cover_url = serializers.SerializerMethodField()
    variants = ItemVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            "item_id",
            "item",
            "item_quantity",
            "item_price",
            "author",
            "item_code",
            "isbn",
            "badge",
            "cover_url",
            "category",
            "category_name",
            "tax_exempt",
            "student_discount_exempt",
            "tax_exempt_from_category",
            "student_discount_exempt_from_category",
            "variants",
        ]
        read_only_fields = [
            "category_name",
            "cover_url",
            "tax_exempt_from_category",
            "student_discount_exempt_from_category",
        ]

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", None))
        if category and category.category_name.casefold() == "apparel":
            if (
                self.instance
                and self.instance.is_apparel
                and "item_quantity" in attrs
                and attrs["item_quantity"] != self.instance.item_quantity
            ):
                raise serializers.ValidationError({
                    "item_quantity": "Manage apparel stock through its size and color variants."
                })
        elif self.instance and self.instance.is_apparel and self.instance.variants.exists():
            raise serializers.ValidationError({
                "category": "Remove this item's variants before changing its category."
            })
        return attrs

    def create(self, validated_data):
        item = super().create(validated_data)
        if item.is_apparel and item.item_quantity:
            ItemVariant.objects.create(
                item=item,
                size="Unspecified",
                color="Unspecified",
                quantity=item.item_quantity,
            )
        return item

    def update(self, instance, validated_data):
        # An exemption sent for this item is the item's own choice, which takes priority
        # over its category: toggling the category later will not change it.
        for field in Category.CASCADED_EXEMPTIONS:
            if field in validated_data:
                validated_data[f"{field}_from_category"] = False
        was_apparel = instance.is_apparel
        item = super().update(instance, validated_data)
        if item.is_apparel and not was_apparel and item.item_quantity:
            ItemVariant.objects.create(
                item=item,
                size="Unspecified",
                color="Unspecified",
                quantity=item.item_quantity,
            )
        return item

    def get_cover_url(self, obj):
        if obj.cover_url:
            return obj.cover_url
        if not obj.isbn:
            return ""

        return f"https://covers.openlibrary.org/b/isbn/{obj.isbn}-L.jpg"


class CartItemSerializer(serializers.ModelSerializer):
    item_details = ItemSerializer(
        source="item",
        read_only=True,
    )

    item_name = serializers.CharField(
        source="item.item",
        read_only=True,
    )

    item_price = serializers.DecimalField(
        source="item.item_price",
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )

    subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    customer_discount_amount = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()
    variant_id = serializers.IntegerField(read_only=True)
    variant_size = serializers.CharField(
        source="variant.size",
        read_only=True,
        allow_null=True,
    )
    variant_color = serializers.CharField(
        source="variant.color",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "item",
            "item_details",
            "variant_id",
            "variant_size",
            "variant_color",
            "item_name",
            "item_price",
            "quantity",
            "subtotal",
            "discount_amount",
            "customer_discount_amount",
            "tax_amount",
            "line_total",
        ]

    def _price(self, obj):
        return price_line(
            obj.item,
            obj.quantity,
            self.context.get("customer_discount_type"),
        )

    def get_subtotal(self, obj):
        return self._price(obj).subtotal

    def get_discount_amount(self, obj):
        return self._price(obj).category_discount

    def get_customer_discount_amount(self, obj):
        return self._price(obj).customer_discount

    def get_tax_amount(self, obj):
        return self._price(obj).tax

    def get_line_total(self, obj):
        price = self._price(obj)
        return price.subtotal - price.customer_discount + price.tax


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    discount_total = serializers.SerializerMethodField()
    customer_discount_type = serializers.SerializerMethodField()
    customer_discount_percent = serializers.SerializerMethodField()
    customer_discount_amount = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            "cart_items",
            "total_items",
            "subtotal",
            "discount_total",
            "customer_discount_type",
            "customer_discount_percent",
            "customer_discount_amount",
            "tax_amount",
            "total_price",
            "created_at",
            "updated_at",
        ]

    def get_total_items(self, obj):
        return sum(
            cart_item.quantity
            for cart_item in obj.cart_items.all()
        )

    def _sum_lines(self, obj, field):
        return sum(
            getattr(
                price_line(
                    cart_item.item,
                    cart_item.quantity,
                    self.context.get("customer_discount_type"),
                ),
                field,
            )
            for cart_item in obj.cart_items.all()
        )

    def get_subtotal(self, obj):
        return self._sum_lines(obj, "subtotal")

    def get_discount_total(self, obj):
        return self._sum_lines(obj, "category_discount")

    def get_customer_discount_type(self, obj):
        return self.context.get("customer_discount_type") or ""

    def get_customer_discount_percent(self, obj):
        return customer_discount_percent(self.context.get("customer_discount_type"))

    def get_customer_discount_amount(self, obj):
        return self._sum_lines(obj, "customer_discount")

    def get_tax_amount(self, obj):
        return self._sum_lines(obj, "tax")

    def get_total_price(self, obj):
        return (
            self.get_subtotal(obj)
            - self.get_customer_discount_amount(obj)
            + self.get_tax_amount(obj)
        )


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = [
            "item_name",
            "item_code",
            "variant_size",
            "variant_color",
            "quantity",
            "unit_price",
            "discount_type",
            "discount_value",
            "discount_amount",
            "customer_discount_amount",
            "line_total",
            "tax_amount",
        ]


class SaleReceiptSerializer(serializers.ModelSerializer):
    issued_at = serializers.DateTimeField(source="created_at", read_only=True)
    items = SaleItemSerializer(source="sale_items", many=True, read_only=True)

    class Meta:
        model = Sale
        fields = [
            "receipt_number",
            "issued_at",
            "items",
            "subtotal",
            "discount_total",
            "customer_discount_type",
            "customer_discount_percent",
            "customer_discount_amount",
            "tax_amount",
            "total",
            "payment_method",
            "cash_received",
            "change_due",
        ]