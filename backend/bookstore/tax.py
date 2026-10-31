from decimal import Decimal, ROUND_HALF_UP


TAX_RATE = Decimal("0.0825")
CENT = Decimal("0.01")


def calculate_amount_tax(item, amount):
    category = item.category
    if item.tax_exempt or category.tax_exempt:
        return Decimal("0.00")

    return (amount * TAX_RATE).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def calculate_line_tax(item, quantity):
    return calculate_amount_tax(item, item.item_price * quantity)
