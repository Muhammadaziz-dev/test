# analytics/selectors/product_tops.py
from django.db.models import Sum, Value, F, DecimalField, IntegerField, ExpressionWrapper, Case, When
from django.db.models.functions import Coalesce
from django.core.exceptions import FieldError
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_products_top_list(date_from, date_to, store_id, *, by='profit', limit=10):
    """
    by: 'profit' | 'quantity'
    Natija: {'rows': [ {product_id, product_name, quantity, profit_usd}, ...], 'source': '...'}
    """
    ProductSale = get_model('ProductSale')
    if not ProductSale:
        return {'rows': [], 'source': 'ProductSale not found'}

    # maydonlar
    product_fk = find_field(ProductSale, ['product'])
    qty_field   = find_field(ProductSale, ['quantity', 'qty', 'count'])
    profit_field= find_field(ProductSale, ['profit'])

    if not (product_fk and qty_field):
        return {'rows': [], 'source': 'ProductSale missing product/quantity'}

    kwargs_ps = date_range_kwargs(ProductSale, date_from, date_to)
    qs = ProductSale.objects.filter(**kwargs_ps)
    qs = try_filter_store(qs, store_id, ['order__store_id', 'store_id', 'order__store__id'])

    # soft-delete bo'lsa chiqaramiz
    for flag in ['is_deleted', 'deleted']:
        if find_field(ProductSale, [flag]):
            qs = qs.filter(**{flag: False})
            break

    # foyda USD
    if profit_field:
        if find_field(ProductSale, ['currency']) and find_field(ProductSale, ['exchange_rate']):
            qs = qs.annotate(_profit_usd=as_usd(profit_field, 'currency', 'exchange_rate'))
        else:
            qs = qs.annotate(_profit_usd=ExpressionWrapper(F(profit_field),
                        output_field=DecimalField(max_digits=20, decimal_places=6)))
        profit_src = f'ProductSale.{profit_field}'
    else:
        # fallback: profit yo'q bo'lsa 0
        qs = qs.annotate(_profit_usd=Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))
        profit_src = 'no ProductSale.profit (0)'

    # guruhlash
    try:
        grouped = qs.values(f'{product_fk}', f'{product_fk}__name').annotate(
            product_id=F(f'{product_fk}'),
            product_name=Coalesce(F(f'{product_fk}__name'), Value('')),
            quantity=Coalesce(Sum(qty_field, output_field=IntegerField()), Value(0)),
            profit_usd=Coalesce(Sum('_profit_usd'), Value(D0),
                                output_field=DecimalField(max_digits=20, decimal_places=6)),
        )
    except FieldError:
        # product__name bo'lmasa (nom maydoni boshqa) — faqat ID qaytaramiz
        grouped = qs.values(f'{product_fk}').annotate(
            product_id=F(f'{product_fk}'),
            product_name=Value('', output_field=DecimalField(max_digits=20, decimal_places=0)),  # dummy
            quantity=Coalesce(Sum(qty_field, output_field=IntegerField()), Value(0)),
            profit_usd=Coalesce(Sum('_profit_usd'), Value(D0),
                                output_field=DecimalField(max_digits=20, decimal_places=6)),
        )

    rows = list(grouped)

    # tartiblash
    if by == 'quantity':
        rows.sort(key=lambda x: x['quantity'], reverse=True)
        src = f'group by product; Σ({qty_field}); profit via {profit_src}'
    else:
        rows.sort(key=lambda x: x['profit_usd'], reverse=True)
        src = f'group by product; Σ(profit); profit via {profit_src}'

    if limit and limit > 0:
        rows = rows[:limit]

    # product_name bo'sh bo'lsa string bo'lishini ta'minlaymiz
    for r in rows:
        if r.get('product_name') is None:
            r['product_name'] = ''

    return {'rows': rows, 'source': src}


def compute_product_headliners(date_from, date_to, store_id):
    """
    Eng ko'p daromadli va eng ko'p sotilgan bitta-bittadan mahsulotni qaytaradi.
    """
    top_profit = compute_products_top_list(date_from, date_to, store_id, by='profit', limit=1)
    top_qty    = compute_products_top_list(date_from, date_to, store_id, by='quantity', limit=1)

    return {
        'top_profit_product': (top_profit['rows'][0] if top_profit['rows'] else None),
        'top_sold_product':   (top_qty['rows'][0] if top_qty['rows'] else None),
        'sources': {
            'top_profit': top_profit['source'],
            'top_quantity': top_qty['source'],
        }
    }
