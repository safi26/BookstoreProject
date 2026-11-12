from collections import namedtuple
from decimal import Decimal, ROUND_HALF_UP

from .discounts import calculate_discount
from .models import StudentId
from .permissions import user_role
from .tax import CENT, calculate_amount_tax


CUSTOMER_DISCOUNT_RATES = {
    "student": Decimal("0.10"),
    "employee": Decimal("0.20"),
}
INVALID_STUDENT_ID_MESSAGE = "Enter a valid student ID."

# subtotal is after the category discount; the customer discount comes off that.
LinePrice = namedtuple(
    "LinePrice",
    ["original", "category_discount", "subtotal", "customer_discount", "tax"],
)


class InvalidStudentId(Exception):
    pass


def resolve_customer_discount(user, student_id, use_employee_discount):
    role = user_role(user)
    if role == "Operator":
        return "employee"

    if role == "Manager":
        return "employee" if str(use_employee_discount).lower() == "true" else None

    student_id = str(student_id or "").strip()
    if student_id:
        if not StudentId.objects.filter(student_id=student_id, is_active=True).exists():
            raise InvalidStudentId
        return "student"

    return None


def customer_discount_percent(discount_type):
    return CUSTOMER_DISCOUNT_RATES.get(discount_type, Decimal("0")) * 100


def price_line(item, quantity, customer_discount_type=None):
    original = (item.item_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)
    category_discount, subtotal = calculate_discount(
        original,
        item.category.discount_type,
        item.category.discount_value,
    )
    if customer_discount_type == "student" and (
        item.student_discount_exempt or item.category.student_discount_exempt
    ):
        customer_discount_type = None
    rate = CUSTOMER_DISCOUNT_RATES.get(customer_discount_type, Decimal("0"))
    customer_discount = (subtotal * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    tax = calculate_amount_tax(item, subtotal - customer_discount)
    return LinePrice(original, category_discount, subtotal, customer_discount, tax)
