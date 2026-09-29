from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Item, Cart, CartItem
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    CartSerializer,
    CartItemSerializer,
)


User = get_user_model()


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("category_name")
    serializer_class = CategorySerializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = (
        Item.objects
        .select_related("category")
        .all()
        .order_by("item")
    )
    serializer_class = ItemSerializer


class CartView(APIView):

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        cart, created = Cart.objects.get_or_create(user=user)

        serializer = CartSerializer(cart)

        return Response(serializer.data)


    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        cart = get_object_or_404(
            Cart,
            user=user,
        )

        cart.cart_items.all().delete()

        return Response(
            {"message": "Cart cleared successfully."},
            status=status.HTTP_200_OK,
        )


class CartItemCreateView(APIView):

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        item_id = request.data.get("item")
        quantity = request.data.get("quantity", 1)

        if not item_id:
            return Response(
                {"error": "item is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"error": "quantity must be a number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1:
            return Response(
                {"error": "quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = get_object_or_404(
            Item,
            item_id=item_id,
        )

        cart, created = Cart.objects.get_or_create(
            user=user,
        )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            item=item,
            defaults={
                "quantity": quantity,
            },
        )

        if not created:
            new_quantity = cart_item.quantity + quantity

            if new_quantity > item.item_quantity:
                return Response(
                    {
                        "error": (
                            "Requested quantity exceeds "
                            "available inventory."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_item.quantity = new_quantity
            cart_item.save()

        else:
            if quantity > item.item_quantity:
                cart_item.delete()

                return Response(
                    {
                        "error": (
                            "Requested quantity exceeds "
                            "available inventory."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = CartItemSerializer(cart_item)

        return Response(
            serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class CartItemDetailView(APIView):

    def patch(self, request, user_id, cart_item_id):
        user = get_object_or_404(User, id=user_id)

        cart = get_object_or_404(
            Cart,
            user=user,
        )

        cart_item = get_object_or_404(
            CartItem,
            id=cart_item_id,
            cart=cart,
        )

        quantity = request.data.get("quantity")

        if quantity is None:
            return Response(
                {"error": "quantity is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"error": "quantity must be a number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1:
            return Response(
                {"error": "quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity > cart_item.item.item_quantity:
            return Response(
                {
                    "error": (
                        "Requested quantity exceeds "
                        "available inventory."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_item.quantity = quantity
        cart_item.save()

        serializer = CartItemSerializer(cart_item)

        return Response(serializer.data)


    def delete(self, request, user_id, cart_item_id):
        user = get_object_or_404(User, id=user_id)

        cart = get_object_or_404(
            Cart,
            user=user,
        )

        cart_item = get_object_or_404(
            CartItem,
            id=cart_item_id,
            cart=cart,
        )

        cart_item.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )