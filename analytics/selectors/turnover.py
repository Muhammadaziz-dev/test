from decimal import Decimal
from django.db.models import Sum, Value, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_turnover(date_from, date_to, store_id=None, mode='sales'):
    """
    mode: 'sales' (Order.total_price) | 'all' (sales + CashTransaction income-like types)
    Returns: (Decimal turnover, str source)
    """
    turnover = D0
    source = 'none'

    Order = get_model('Order')
    ProductSale = get_model('ProductSale')

    if Order:
        kwargs_t = date_range_kwargs(Order, date_from, date_to)
        qs_t = try_filter_store(Order.objects.filter(**kwargs_t), store_id, ['store_id', 'store__id'])
        for flag in ['is_deleted', 'deleted', 'is_canceled', 'is_cancelled']:
            if find_field(Order, [flag]):
                qs_t = qs_t.filter(**{flag: False})
                break
        price_field = find_field(Order, ['total_price', 'amount', 'sum'])
        if price_field:
            if find_field(Order, ['currency']) and find_field(Order, ['exchange_rate']):
                qs_t = qs_t.annotate(price_usd=as_usd(price_field, 'currency', 'exchange_rate'))
                turnover = qs_t.aggregate(v=Coalesce(Sum('price_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
                source = f'Order.{price_field} (normalized)'
            else:
                turnover = qs_t.aggregate(v=Coalesce(Sum(price_field), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
                source = f'Order.{price_field}'
    elif ProductSale:
        kwargs_ps = date_range_kwargs(ProductSale, date_from, date_to)
        qs_ps = try_filter_store(ProductSale.objects.filter(**kwargs_ps), store_id, ['store_id', 'order__store_id', 'order__store__id'])
        revenue_field = find_field(ProductSale, ['total_price', 'amount', 'line_total', 'sum'])
        unit_price_field = find_field(ProductSale, ['unit_price', 'price'])
        qty_field = find_field(ProductSale, ['quantity', 'qty', 'count'])
        if revenue_field:
            if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
                qs_ps = qs_ps.annotate(revenue_usd=as_usd(revenue_field, 'currency', 'exchange_rate'))
            else:
                qs_ps = qs_ps.annotate(revenue_usd=ExpressionWrapper(F(revenue_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
            turnover = qs_ps.aggregate(v=Coalesce(Sum('revenue_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            source = f'ProductSale.{revenue_field}'
        elif unit_price_field and qty_field:
            if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
                qs_ps = qs_ps.annotate(unit_price_usd=as_usd(unit_price_field, 'currency', 'exchange_rate'))
            else:
                qs_ps = qs_ps.annotate(unit_price_usd=ExpressionWrapper(F(unit_price_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
            qs_ps = qs_ps.annotate(revenue_usd=ExpressionWrapper(F('unit_price_usd') * F(qty_field), output_field=DecimalField(max_digits=20, decimal_places=6)))
            turnover = qs_ps.aggregate(v=Coalesce(Sum('revenue_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            source = 'ProductSale.unit_price*qty'

    if mode in {'all', 'income', 'inflows'}:
        CashTransaction = get_model('CashTransaction')
        if CashTransaction:
            kwargs_ci = date_range_kwargs(CashTransaction, date_from, date_to)
            qs_ci = try_filter_store(CashTransaction.objects.filter(**kwargs_ci), store_id, ['store_id', 'cashbox__store_id', 'store__id'])
            tfield = find_field(CashTransaction, ['type'])
            if tfield:
                qs_ci = qs_ci.filter(**{f"{tfield}__in": ['INCOME', 'REVENUE', 'SALE_INCOME']})
            if find_field(CashTransaction, ['currency']) and find_field(CashTransaction, ['exchange_rate']):
                qs_ci = qs_ci.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
                extra = qs_ci.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            else:
                extra = qs_ci.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            turnover += extra
            source += ' + CashTransaction.INCOME'

    return turnover, source