# analytics/selectors/orders.py
from django.db.models import Sum, Count, Value, F, DecimalField, ExpressionWrapper, Case, When
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_orders_summary(date_from, date_to, store_id=None):
    """
    Returns:
      {
        'orders_count',        # jami buyurtmalar soni
        'revenue_usd',         # Σ total_price (aylanma)
        'profit_usd',          # Σ total_profit (daromad)
        'inflow_usd',          # Σ tushum (paid - change_if_given)
        'unpaid_sum_usd',      # Σ max(total_price - paid, 0)
        'avg_check_usd',       # revenue / orders_count
        'source': '...'
      }
    """
    Order = get_model('Order')
    if not Order:
        return {
            'orders_count': 0, 'revenue_usd': D0, 'profit_usd': D0,
            'inflow_usd': D0, 'unpaid_sum_usd': D0, 'avg_check_usd': D0,
            'source': 'Order not found'
        }

    kwargs_o = date_range_kwargs(Order, date_from, date_to)
    qs = Order.objects.filter(**kwargs_o)
    qs = try_filter_store(qs, store_id, ['store_id', 'store__id'])

    # soft-delete/cancel bayroqlarini chiqaramiz
    for flag in ['is_deleted', 'deleted', 'is_canceled', 'is_cancelled']:
        if find_field(Order, [flag]):
            qs = qs.filter(**{flag: False})
            break

    price_field  = find_field(Order, ['total_price', 'amount', 'sum']) or 'total_price'
    profit_field = find_field(Order, ['total_profit', 'profit']) or 'total_profit'
    paid_field   = find_field(Order, ['paid_amount', 'paid', 'payment', 'paid_sum'])
    change_flag  = find_field(Order, ['change_given'])
    change_field = find_field(Order, ['change_amount'])

    has_fx = find_field(Order, ['currency']) and find_field(Order, ['exchange_rate'])

    price_usd = as_usd(price_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(price_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    profit_usd = as_usd(profit_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(profit_field), output_field=DecimalField(max_digits=20, decimal_places=6))

    if paid_field:
        paid_usd = as_usd(paid_field, 'currency', 'exchange_rate') if has_fx else \
            ExpressionWrapper(F(paid_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    else:
        paid_usd = Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6))

    if change_field:
        change_usd = as_usd(change_field, 'currency', 'exchange_rate') if has_fx else \
            ExpressionWrapper(F(change_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    else:
        change_usd = Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6))

    # Inflow = paid - change (agar change_given True bo‘lsa), aks holda paid
    inflow_expr = Case(
        When(**{f'{change_flag}': True}, then=F('_paid_usd') - F('_change_usd')) if change_flag else Value(None),
        default=F('_paid_usd'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    )

    qs = qs.annotate(
        _price_usd=price_usd,
        _profit_usd=profit_usd,
        _paid_usd=paid_usd,
        _change_usd=change_usd,
    ).annotate(
        _inflow_usd=inflow_expr,
        _diff=ExpressionWrapper(F('_price_usd') - F('_paid_usd'),
                                output_field=DecimalField(max_digits=20, decimal_places=6)),
        unpaid_usd=Case(
            When(_diff__gt=Value(D0), then=F('_diff')),
            default=Value(D0),
            output_field=DecimalField(max_digits=20, decimal_places=6),
        )
    )

    agg = qs.aggregate(
        orders_count=Coalesce(Count('id'), Value(0)),
        revenue_usd=Coalesce(Sum('_price_usd'), Value(D0),  output_field=DecimalField(max_digits=20, decimal_places=6)),
        profit_usd=Coalesce(Sum('_profit_usd'), Value(D0),  output_field=DecimalField(max_digits=20, decimal_places=6)),
        inflow_usd=Coalesce(Sum('_inflow_usd'), Value(D0),  output_field=DecimalField(max_digits=20, decimal_places=6)),
        unpaid_sum_usd=Coalesce(Sum('unpaid_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
    )

    orders = agg['orders_count'] or 0
    revenue = agg['revenue_usd'] or D0
    agg['avg_check_usd'] = (revenue / orders) if orders else D0
    agg['source'] = "Order normalized: Σ(total_price, total_profit, inflow=paid-change, unpaid=max(price-paid,0))"
    return agg
