from decimal import Decimal, ROUND_HALF_UP

from .models import StudentId
from .tax import CENT, calculate_line_tax


DISCOUNT_RATES = {
    "student": Decimal("0.10"),
    "employee": Decimal("0.20"),
}
INVALID_STUDENT_ID_MESSAGE = "Enter a valid student ID."


class InvalidStudentId(Exception):
    pass


def resolve_discount(role, student_id, use_employee_discount):
    if role == "Operator":
        return "employee"

    if role == "Manager":
        return "employee" if str(use_employee_discount).lower() == "true" else None

    student_id = str(student_id or "").strip()
    if role == "Student" and student_id:
        if not StudentId.objects.filter(student_id=student_id, is_active=True).exists():
            raise InvalidStudentId
        return "student"

    return None


def discount_percent(discount_type):
    return DISCOUNT_RATES.get(discount_type, Decimal("0")) * 100


def price_line(item, quantity, discount_type=None):
    subtotal = item.item_price * quantity
    rate = DISCOUNT_RATES.get(discount_type, Decimal("0"))
    discount = (subtotal * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    tax = calculate_line_tax(item, subtotal - discount)
    return subtotal, discount, tax
