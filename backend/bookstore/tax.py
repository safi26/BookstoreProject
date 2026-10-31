from decimal import Decimal, ROUND_HALF_UP


TAX_RATE = Decimal("0.0825")
CENT = Decimal("0.01")


def calculate_line_tax(item, taxable_amount):
    category = item.category
    if item.tax_exempt or category.tax_exempt:
        return Decimal("0.00")

    return (taxable_amount * TAX_RATE).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )
