from rest_framework import serializers

from .models import Category, Item, Cart, CartItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "category_id",
            "category_name",
        ]


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.category_name",
        read_only=True,
    )

    class Meta:
        model = Item
        fields = [
            "item_id",
            "item",
            "item_quantity",
            "item_price",
            "category",
            "category_name",
        ]


class CartItemSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = CartItem
        fields = [
            "id",
            "item",
            "item_name",
            "item_price",
            "quantity",
            "subtotal",
        ]

    def get_subtotal(self, obj):
        return obj.item.item_price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            "cart_items",
            "total_items",
            "total_price",
            "created_at",
            "updated_at",
        ]

    def get_total_items(self, obj):
        return sum(
            cart_item.quantity
            for cart_item in obj.cart_items.all()
        )

    def get_total_price(self, obj):
        return sum(
            cart_item.item.item_price * cart_item.quantity
            for cart_item in obj.cart_items.all()
        )