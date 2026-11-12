from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def calculate_discount(line_subtotal, discount_type, discount_value):
    if discount_type == "percent":
        amount = (line_subtotal * discount_value / Decimal("100")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
    elif discount_type == "dollar":
        amount = discount_value
    else:
        amount = Decimal("0.00")

    amount = min(line_subtotal, amount).quantize(CENT, rounding=ROUND_HALF_UP)
    return amount, (line_subtotal - amount).quantize(CENT, rounding=ROUND_HALF_UP)
