from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Category, Item, ItemVariant, Cart, CartItem, Sale, SaleItem
from .permissions import IsCartOwner, IsManager, IsManagerOrReadOnly, user_role
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    ItemVariantSerializer,
    CartSerializer,
    CartItemSerializer,
    SaleReceiptSerializer,
)
from .pricing import (
    INVALID_STUDENT_ID_MESSAGE,
    InvalidStudentId,
    customer_discount_percent,
    price_line,
    resolve_customer_discount,
)


User = get_user_model()


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("category_name")
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.items.exists():
            return Response(
                {"detail": "Move or remove this category's items before deleting it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class ItemViewSet(viewsets.ModelViewSet):
    queryset = (
        Item.objects
        .select_related("category")
        .all()
        .order_by("item")
    )
    serializer_class = ItemSerializer
    permission_classes = [IsManagerOrReadOnly]

class ItemVariantCollectionView(APIView):
    permission_classes = [IsManagerOrReadOnly]

    def get_item(self, item_id):
        item = get_object_or_404(Item.objects.select_related("category"), pk=item_id)
        if not item.is_apparel:
            return None, Response(
                {"error": "Only apparel items have size and color variants."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return item, None

    def get(self, request, item_id):
        item, error = self.get_item(item_id)
        if error:
            return error
        variants = item.variants.all()
        return Response(ItemVariantSerializer(variants, many=True).data)

    def post(self, request, item_id):
        item, error = self.get_item(item_id)
        if error:
            return error
        serializer = ItemVariantSerializer(
            data=request.data,
            context={"item": item},
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(item=item)
            item.item_quantity = sum(item.variants.values_list("quantity", flat=True))
            item.save(update_fields=["item_quantity"])
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ItemVariantDetailView(APIView):
    permission_classes = [IsManagerOrReadOnly]

    def get_variant(self, item_id, variant_id):
        item = get_object_or_404(Item.objects.select_related("category"), pk=item_id)
        if not item.is_apparel:
            return None, None, Response(
                {"error": "Only apparel items have size and color variants."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        variant = get_object_or_404(item.variants, pk=variant_id)
        return item, variant, None

    def patch(self, request, item_id, variant_id):
        item, variant, error = self.get_variant(item_id, variant_id)
        if error:
            return error
        serializer = ItemVariantSerializer(variant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
            item.item_quantity = sum(item.variants.values_list("quantity", flat=True))
            item.save(update_fields=["item_quantity"])
        return Response(serializer.data)

    def get(self, request, item_id, variant_id):
        _, variant, error = self.get_variant(item_id, variant_id)
        if error:
            return error
        return Response(ItemVariantSerializer(variant).data)

    def delete(self, request, item_id, variant_id):
        item, variant, error = self.get_variant(item_id, variant_id)
        if error:
            return error
        if variant.quantity:
            return Response(
                {"error": "Set this variant's stock to zero before deleting it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if variant.cart_items.exists():
            return Response(
                {"error": "Remove this variant from carts before deleting it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            variant.delete()
            item.item_quantity = sum(item.variants.values_list("quantity", flat=True))
            item.save(update_fields=["item_quantity"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Sale.objects
        .prefetch_related("sale_items")
        .all()
        .order_by("-created_at", "-pk")
    )
    serializer_class = SaleReceiptSerializer
    lookup_field = "receipt_number"
    permission_classes = [IsManager]


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        user_id = request.data.get("user_id")
        password = request.data.get("password")
        if (
            not isinstance(user_id, (str, int))
            or isinstance(user_id, bool)
            or not str(user_id).isdecimal()
            or not isinstance(password, str)
            or not password
        ):
            return Response(
                {"detail": "Enter a valid user ID and password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(pk=int(user_id)).first()
        authenticated_user = (
            authenticate(
                request,
                username=user.get_username(),
                password=password,
            )
            if user is not None
            else None
        )
        if authenticated_user is None:
            return Response(
                {"detail": "Invalid user ID or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=authenticated_user)
        return Response({
            "token": token.key,
            "user_id": authenticated_user.pk,
            "role": user_role(authenticated_user),
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartView(APIView):
    permission_classes = [IsCartOwner]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        try:
            customer_discount_type = resolve_customer_discount(
                request.user,
                request.query_params.get("student_id"),
                request.query_params.get("use_employee_discount"),
            )
        except InvalidStudentId:
            return Response(
                {"error": INVALID_STUDENT_ID_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, created = Cart.objects.get_or_create(user=user)

        serializer = CartSerializer(
            cart,
            context={"customer_discount_type": customer_discount_type},
        )

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
    permission_classes = [IsCartOwner]

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
            Item.objects.select_related("category"),
            item_id=item_id,
        )

        variant = None
        variant_id = request.data.get("variant_id")
        if item.is_apparel:
            if variant_id is None:
                return Response(
                    {"error": "Choose a size and color for this apparel item."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            variant = get_object_or_404(item.variants, pk=variant_id)
        elif variant_id is not None:
            return Response(
                {"error": "Variants can only be selected for apparel items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            stock = variant.quantity if variant else item.item_quantity
            cart, _ = Cart.objects.get_or_create(user=user)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item=item,
                variant=variant,
                defaults={"quantity": quantity},
            )
            new_quantity = quantity if created else cart_item.quantity + quantity
            if new_quantity > stock:
                if created:
                    cart_item.delete()
                return Response(
                    {"error": "Requested quantity exceeds available inventory."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not created:
                cart_item.quantity = new_quantity
                cart_item.save(update_fields=["quantity"])
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
    permission_classes = [IsCartOwner]

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

        available_quantity = (
            cart_item.variant.quantity if cart_item.variant else cart_item.item.item_quantity
        )
        if quantity > available_quantity:
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
    permission_classes = [IsCartOwner]

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

        try:
            customer_discount_type = resolve_customer_discount(
                request.user,
                request.data.get("student_id"),
                request.data.get("use_employee_discount"),
            )
        except InvalidStudentId:
            return Response(
                {"error": INVALID_STUDENT_ID_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                .select_related("item", "variant")
            )
            if not cart_items:
                return Response(
                    {"error": "Your cart is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if "discounts" in request.data:
                return Response(
                    {
                        "error": (
                            "Checkout discounts must be configured by a manager "
                            "on the item's category."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            locked_items = {
                item.pk: item
                for item in Item.objects.select_for_update().filter(
                    pk__in=[cart_item.item_id for cart_item in cart_items]
                ).select_related("category")
            }
            variant_ids = [
                cart_item.variant_id
                for cart_item in cart_items
                if cart_item.variant_id is not None
            ]
            locked_variants = {
                variant.pk: variant
                for variant in ItemVariant.objects.select_for_update().filter(
                    pk__in=variant_ids
                )
            }
            for cart_item in cart_items:
                item = locked_items[cart_item.item_id]
                if item.is_apparel and cart_item.variant_id is None:
                    return Response(
                        {"error": f"Choose a size and color for {item.item}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not item.is_apparel and cart_item.variant_id is not None:
                    return Response(
                        {"error": f"{item.item} does not have size and color variants."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if (
                    cart_item.variant_id is not None
                    and locked_variants[cart_item.variant_id].item_id != item.pk
                ):
                    return Response(
                        {"error": "The selected apparel variant does not match its item."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                stock = (
                    locked_variants[cart_item.variant_id].quantity
                    if cart_item.variant_id is not None
                    else item.item_quantity
                )
                if stock < cart_item.quantity:
                    return Response(
                        {
                            "error": (
                                f"Not enough stock for {item.item}"
                                + (
                                    f" ({cart_item.variant.size}, {cart_item.variant.color})."
                                    if cart_item.variant_id is not None
                                    else "."
                                )
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            line_prices = {
                cart_item.pk: price_line(
                    locked_items[cart_item.item_id],
                    cart_item.quantity,
                    customer_discount_type,
                )
                for cart_item in cart_items
            }
            subtotal = sum(
                (line.subtotal for line in line_prices.values()),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
            discount_total = sum(
                (line.category_discount for line in line_prices.values()),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
            customer_discount_amount = sum(
                (line.customer_discount for line in line_prices.values()),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
            tax_amount = sum(
                (line.tax for line in line_prices.values()),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
            total = subtotal - customer_discount_amount + tax_amount
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
                subtotal=subtotal,
                discount_total=discount_total,
                customer_discount_type=customer_discount_type or "",
                customer_discount_percent=customer_discount_percent(customer_discount_type),
                customer_discount_amount=customer_discount_amount,
                tax_amount=tax_amount,
                total=total,
                cash_received=cash_received,
                change_due=(cash_received - total if cash_received is not None else Decimal("0.00")),
            )

            for cart_item in cart_items:
                item = locked_items[cart_item.item_id]
                line = line_prices[cart_item.pk]
                line_total = (line.subtotal - line.customer_discount).quantize(Decimal("0.01"))
                SaleItem.objects.create(
                    sale=sale,
                    item=item,
                    item_name=item.item,
                    item_code=item.item_code,
                    variant_size=(
                        cart_item.variant.size if cart_item.variant_id else ""
                    ),
                    variant_color=(
                        cart_item.variant.color if cart_item.variant_id else ""
                    ),
                    quantity=cart_item.quantity,
                    unit_price=item.item_price,
                    discount_type=item.category.discount_type,
                    discount_value=item.category.discount_value,
                    discount_amount=line.category_discount,
                    customer_discount_amount=line.customer_discount,
                    line_total=line_total,
                    tax_amount=line.tax,
                )
                if cart_item.variant_id is not None:
                    variant = locked_variants[cart_item.variant_id]
                    variant.quantity -= cart_item.quantity
                    variant.save(update_fields=["quantity"])
                item.item_quantity -= cart_item.quantity
                item.save(update_fields=["item_quantity"])

            cart.cart_items.all().delete()
            serializer = SaleReceiptSerializer(sale)

        return Response(serializer.data, status=status.HTTP_201_CREATED)