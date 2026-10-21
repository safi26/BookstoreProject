from rest_framework import serializers

from .models import Category, Item, Cart, CartItem, Sale, SaleItem
from .tax import calculate_line_tax


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "category_id",
            "category_name",
            "tax_exempt",
        ]


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.category_name",
        read_only=True,
    )
    cover_url = serializers.SerializerMethodField()

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
        ]
        read_only_fields = ["category_name", "cover_url"]

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
    tax_amount = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "item",
            "item_details",
            "item_name",
            "item_price",
            "quantity",
            "subtotal",
            "tax_amount",
            "line_total",
        ]

    def get_subtotal(self, obj):
        return obj.item.item_price * obj.quantity

    def get_tax_amount(self, obj):
        return calculate_line_tax(obj.item, obj.quantity)

    def get_line_total(self, obj):
        return self.get_subtotal(obj) + self.get_tax_amount(obj)


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
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

    def get_subtotal(self, obj):
        return sum(
            cart_item.item.item_price * cart_item.quantity
            for cart_item in obj.cart_items.all()
        )

    def get_tax_amount(self, obj):
        return sum(
            calculate_line_tax(cart_item.item, cart_item.quantity)
            for cart_item in obj.cart_items.all()
        )

    def get_total_price(self, obj):
        return self.get_subtotal(obj) + self.get_tax_amount(obj)


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = [
            "item_name",
            "item_code",
            "quantity",
            "unit_price",
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
            "tax_amount",
            "total",
            "payment_method",
            "cash_received",
            "change_due",
        ]