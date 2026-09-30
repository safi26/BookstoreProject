from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Item, Cart, CartItem, Sale, SaleItem
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    CartSerializer,
    CartItemSerializer,
    SaleReceiptSerializer,
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


class CheckoutView(APIView):

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        payment_method = request.data.get("payment_method")
        if payment_method not in {"cash", "card"}:
            return Response(
                {"error": "payment_method must be cash or card."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cash_received = None
        if payment_method == "cash":
            try:
                cash_received = Decimal(str(request.data.get("cash_received", "")))
            except (InvalidOperation, TypeError, ValueError):
                return Response(
                    {"error": "Enter a valid cash amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if (
                not cash_received.is_finite()
                or cash_received < 0
                or cash_received > Decimal("99999999.99")
            ):
                return Response(
                    {"error": "Enter a valid non-negative cash amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cash_received = cash_received.quantize(Decimal("0.01"))

        with transaction.atomic():
            cart = Cart.objects.select_for_update().filter(user=user).first()
            if cart is None:
                return Response(
                    {"error": "Your cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_items = list(
                CartItem.objects
                .select_for_update()
                .filter(cart=cart)
                .select_related("item")
            )
            if not cart_items:
                return Response(
                    {"error": "Your cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            locked_items = {
                item.pk: item
                for item in Item.objects.select_for_update().filter(
                    pk__in=[cart_item.item_id for cart_item in cart_items]
                )
            }
            for cart_item in cart_items:
                item = locked_items[cart_item.item_id]
                if item.item_quantity < cart_item.quantity:
                    return Response(
                        {"error": f"Not enough stock for {item.item}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            total = sum(
                (locked_items[cart_item.item_id].item_price * cart_item.quantity
                 for cart_item in cart_items),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
            if payment_method == "cash" and cash_received < total:
                return Response(
                    {"error": "Cash received must cover the cart total."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sale = Sale.objects.create(
                user=user,
                receipt_number=(
                    f"CP-{timezone.now():%Y%m%d}-{uuid4().hex[:6].upper()}"
                ),
                payment_method=payment_method,
                total=total,
                cash_received=cash_received,
                change_due=(cash_received - total if cash_received is not None else Decimal("0.00")),
            )

            for cart_item in cart_items:
                item = locked_items[cart_item.item_id]
                line_total = (item.item_price * cart_item.quantity).quantize(Decimal("0.01"))
                SaleItem.objects.create(
                    sale=sale,
                    item=item,
                    item_name=item.item,
                    item_code=item.item_code,
                    quantity=cart_item.quantity,
                    unit_price=item.item_price,
                    line_total=line_total,
                )
                item.item_quantity -= cart_item.quantity
                item.save(update_fields=["item_quantity"])

            cart.cart_items.all().delete()
            serializer = SaleReceiptSerializer(sale)

        return Response(serializer.data, status=status.HTTP_201_CREATED)