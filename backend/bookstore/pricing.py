from collections import namedtuple
from decimal import Decimal, ROUND_HALF_UP

from .discounts import calculate_discount
from .models import StudentId, Voucher
from .permissions import user_role
from .tax import CENT, calculate_amount_tax


CUSTOMER_DISCOUNT_RATES = {
    "student": Decimal("0.10"),
    "employee": Decimal("0.20"),
}
INVALID_STUDENT_ID_MESSAGE = "Enter a valid student ID or voucher ID."
EMPTY_VOUCHER_MESSAGE = "This voucher has no remaining balance."

# subtotal is after the category discount; the customer discount comes off that.
LinePrice = namedtuple(
    "LinePrice",
    ["original", "category_discount", "subtotal", "customer_discount", "tax"],
)


class InvalidStudentId(Exception):
    def __init__(self, message=INVALID_STUDENT_ID_MESSAGE):
        super().__init__(message)
        self.message = message


def find_voucher(code, for_update=False):
    code = str(code or "").strip()
    if not code:
        return None
    vouchers = Voucher.objects.filter(voucher_id=code, is_active=True)
    if for_update:
        vouchers = vouchers.select_for_update()
    return vouchers.first()


def voucher_split(voucher, total):
    total = Decimal(total).quantize(CENT, rounding=ROUND_HALF_UP)
    if voucher is None:
        return Decimal("0.00"), total
    applied = min(voucher.balance, total).quantize(CENT, rounding=ROUND_HALF_UP)
    return applied, (total - applied).quantize(CENT, rounding=ROUND_HALF_UP)


def resolve_customer_discount(user, student_id, use_employee_discount):
    role = user_role(user)
    if role == "Operator":
        return "employee"

    if role == "Manager":
        return "employee" if str(use_employee_discount).lower() == "true" else None

    student_id = str(student_id or "").strip()
    if student_id:
        if StudentId.objects.filter(student_id=student_id, is_active=True).exists():
            return "student"
        voucher = find_voucher(student_id)
        if voucher is None:
            raise InvalidStudentId
        if voucher.balance <= 0:
            raise InvalidStudentId(EMPTY_VOUCHER_MESSAGE)
        return None

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
    elif customer_discount_type == "employee" and item.category.employee_discount_exempt:
        customer_discount_type = None
    rate = CUSTOMER_DISCOUNT_RATES.get(customer_discount_type, Decimal("0"))
    customer_discount = (subtotal * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    tax = calculate_amount_tax(item, subtotal - customer_discount)
    return LinePrice(original, category_discount, subtotal, customer_discount, tax)
