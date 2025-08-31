from decimal import Decimal
from django.db.models import Case, When, F, Value, DecimalField, ExpressionWrapper

D0 = Decimal('0')


def as_usd(amount='amount', currency='currency', rate='exchange_rate'):
    rate_safe = Case(
        When(**{f"{rate}__gt": D0}, then=F(rate)),
        default=Value(Decimal('1')),
        output_field=DecimalField(max_digits=20, decimal_places=6),
    )
    to_usd = ExpressionWrapper(
        F(amount) / rate_safe,
        output_field=DecimalField(max_digits=20, decimal_places=6),
    )
    return Case(
        When(**{currency: 'UZS'}, then=to_usd),
        default=F(amount),
        output_field=DecimalField(max_digits=20, decimal_places=6),
    )