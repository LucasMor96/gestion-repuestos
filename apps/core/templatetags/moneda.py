from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template


register = template.Library()


@register.filter
def ars(value):
    """Format a monetary value using Argentine peso notation: $ 8.370."""
    if value is None or value == "":
        return "$ 0"

    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return value

    if amount == amount.to_integral():
        number = f"{int(amount):,}".replace(",", ".")
    else:
        whole, decimals = f"{amount:,.2f}".split(".", 1)
        number = whole.replace(",", ".") + "," + decimals

    return f"$ {number}"
