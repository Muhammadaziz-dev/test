# analytics/selectors/product_sales.py
from django.db.models import Sum, Value, F, DecimalField, IntegerField, ExpressionWrapper
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_product_sales(date_from, date_to, store_id=None, *, order_by='quantity', limit=50):
    """
    Mahsulotlar sotuvi (period ichida):
      - product_id, product_name
      - quantity (Σ)
      - revenue_usd (Σ line_total)
      - profit_usd  (Σ)
      - avg_unit_price_usd = revenue / quantity
    order_by: 'quantity' | 'revenue' | 'profit'
    """
    ProductSale = get_model('ProductSale')
    if not ProductSale:
        return {'products': [], 'source': 'ProductSale not found'}

    product_fk  = find_field(ProductSale, ['product'])
    qty_field   = find_field(ProductSale, ['quantity', 'qty', 'count'])
    total_field = find_field(ProductSale, ['total_price', 'amount', 'sum'])
    unit_field  = find_field(ProductSale, ['unit_price', 'price'])
    profit_field= find_field(ProductSale, ['profit'])

    if not (product_fk and qty_field):
        return {'products': [], 'source': 'ProductSale missing product/quantity'}

    kwargs_ps = date_range_kwargs(ProductSale, date_from, date_to)
    qs = ProductSale.objects.filter(**kwargs_ps)
    qs = try_filter_store(qs, store_id, ['order__store_id', 'store_id', 'order__store__id'])

    # revenue: total_price agar bo‘lsa; aks holda unit_price * qty
    if total_field:
        if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
            qs = qs.annotate(_rev_usd=as_usd(total_field, 'currency', 'exchange_rate'))
        else:
            qs = qs.annotate(_rev_usd=ExpressionWrapper(F(total_field),
                         output_field=DecimalField(max_digits=20, decimal_places=6)))
        rev_src = f'ProductSale.{total_field}'
    elif unit_field:
        if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
            qs = qs.annotate(_unit_usd=as_usd(unit_field, 'currency', 'exchange_rate'))
        else:
            qs = qs.annotate(_unit_usd=ExpressionWrapper(F(unit_field),
                         output_field=DecimalField(max_digits=20, decimal_places=6)))
        qs = qs.annotate(_rev_usd=ExpressionWrapper(F('_unit_usd') * F(qty_field),
                         output_field=DecimalField(max_digits=20, decimal_places=6)))
        rev_src = f'ProductSale.{unit_field}*{qty_field}'
    else:
        qs = qs.annotate(_rev_usd=Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))
        rev_src = 'missing total/unit -> 0'

    # profit
    if profit_field:
        if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
            qs = qs.annotate(_profit_usd=as_usd(profit_field, 'currency', 'exchange_rate'))
        else:
            qs = qs.annotate(_profit_usd=ExpressionWrapper(F(profit_field),
                         output_field=DecimalField(max_digits=20, decimal_places=6)))
        prof_src = f'ProductSale.{profit_field}'
    else:
        qs = qs.annotate(_profit_usd=Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))
        prof_src = 'missing profit -> 0'

    grouped = qs.values(f'{product_fk}', f'{product_fk}__name').annotate(
        product_id=F(f'{product_fk}'),
        product_name=Coalesce(F(f'{product_fk}__name'), Value('')),
        quantity=Coalesce(Sum(qty_field, output_field=IntegerField()), Value(0)),
        revenue_usd=Coalesce(Sum('_rev_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        profit_usd=Coalesce(Sum('_profit_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
    )

    rows = list(grouped)
    # avg price
    for r in rows:
        q = int(r['quantity'] or 0)
        rev = r['revenue_usd'] or D0
        r['avg_unit_price_usd'] = (rev / q) if q else D0

    # sort
    key_map = {
        'quantity': lambda x: x['quantity'],
        'revenue':  lambda x: x['revenue_usd'],
        'profit':   lambda x: x['profit_usd'],
    }
    rows.sort(key=key_map.get(order_by, key_map['quantity']), reverse=True)
    if limit and limit > 0:
        rows = rows[:limit]

    return {
        'products': rows,
        'source': f'group by product; revenue via {rev_src}; profit via {prof_src}'
    }
