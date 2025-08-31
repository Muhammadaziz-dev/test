from decimal import Decimal
from django.db.models import Sum, Value, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_gross_profit(date_from, date_to, store_id=None):
    """Order.total_profit first; fallback ProductSale (profit or revenue-COGS)."""
    gross = D0
    source = 'none'

    Order = get_model('Order')
    ProductSale = get_model('ProductSale')

    if Order:
        kwargs_o = date_range_kwargs(Order, date_from, date_to)
        qs_o = try_filter_store(Order.objects.filter(**kwargs_o), store_id, ['store_id', 'store__id'])
        for flag in ['is_deleted', 'deleted', 'is_canceled', 'is_cancelled']:
            if find_field(Order, [flag]):
                qs_o = qs_o.filter(**{flag: False})
                break
        ofield = find_field(Order, ['total_profit', 'profit'])
        if ofield:
            if find_field(Order, ['currency']) and find_field(Order, ['exchange_rate']):
                qs_o = qs_o.annotate(profit_usd=as_usd(ofield, 'currency', 'exchange_rate'))
                gross = qs_o.aggregate(v=Coalesce(Sum('profit_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
                source = f'Order.{ofield} (normalized)'
            else:
                gross = qs_o.aggregate(v=Coalesce(Sum(ofield), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
                source = f'Order.{ofield}'

    if (gross == D0) and ProductSale:
        kwargs_ps = date_range_kwargs(ProductSale, date_from, date_to)
        qs_ps = try_filter_store(ProductSale.objects.filter(**kwargs_ps), store_id, ['store_id', 'order__store_id', 'order__store__id'])
        pfield = find_field(ProductSale, ['profit'])
        if pfield:
            if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
                qs_ps = qs_ps.annotate(profit_usd=as_usd(pfield, 'currency', 'exchange_rate'))
                gross = qs_ps.aggregate(v=Coalesce(Sum('profit_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
                source = f'ProductSale.{pfield} (normalized)'
            else:
                gross = qs_ps.aggregate(v=Coalesce(Sum(pfield), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
                source = f'ProductSale.{pfield}'
        else:
            revenue_field = find_field(ProductSale, ['total_price', 'amount', 'line_total', 'sum'])
            unit_price_field = find_field(ProductSale, ['unit_price', 'price'])
            qty_field = find_field(ProductSale, ['quantity', 'qty', 'count'])
            cogs_field = find_field(ProductSale, ['cogs'])
            unit_cost_field = find_field(ProductSale, ['unit_cost', 'cost', 'purchase_price'])

            if revenue_field:
                if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
                    qs_ps = qs_ps.annotate(revenue_usd=as_usd(revenue_field, 'currency', 'exchange_rate'))
                else:
                    qs_ps = qs_ps.annotate(revenue_usd=ExpressionWrapper(F(revenue_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
            elif unit_price_field and qty_field:
                if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
                    qs_ps = qs_ps.annotate(unit_price_usd=as_usd(unit_price_field, 'currency', 'exchange_rate'))
                else:
                    qs_ps = qs_ps.annotate(unit_price_usd=ExpressionWrapper(F(unit_price_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
                qs_ps = qs_ps.annotate(revenue_usd=ExpressionWrapper(F('unit_price_usd') * F(qty_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
            else:
                qs_ps = qs_ps.annotate(revenue_usd=Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))

            if cogs_field:
                if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
                    qs_ps = qs_ps.annotate(cogs_usd=as_usd(cogs_field, 'currency', 'exchange_rate'))
                else:
                    qs_ps = qs_ps.annotate(cogs_usd=ExpressionWrapper(F(cogs_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
                inner_src = 'ProductSale.cogs'
            elif unit_cost_field and qty_field:
                if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
                    qs_ps = qs_ps.annotate(unit_cost_usd=as_usd(unit_cost_field, 'currency', 'exchange_rate'))
                else:
                    qs_ps = qs_ps.annotate(unit_cost_usd=ExpressionWrapper(F(unit_cost_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
                qs_ps = qs_ps.annotate(cogs_usd=ExpressionWrapper(F('unit_cost_usd') * F(qty_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
                inner_src = 'unit_cost*qty'
            else:
                qs_ps = qs_ps.annotate(cogs_usd=Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))
                inner_src = 'cogs=0'

            qs_ps = qs_ps.annotate(gross_profit_usd=ExpressionWrapper(F('revenue_usd') - F('cogs_usd'), output_field=DecimalField(max_digits=20, decimal_places=6)))
            gross = qs_ps.aggregate(v=Coalesce(Sum('gross_profit_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            source = f'revenue-COGS ({inner_src})'

    return gross, source