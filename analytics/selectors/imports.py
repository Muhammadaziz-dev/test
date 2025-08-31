# analytics/selectors/imports.py
from django.db.models import Sum, Value, F, DecimalField, ExpressionWrapper, IntegerField
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, date_range_kwargs, try_filter_store, find_field
from ..utils.money import as_usd, D0

def compute_imports(date_from, date_to, store_id=None, *, mode='pure'):
    """
    mode:
      - 'pure' -> debt bilan bog'liq kirimlarni chiqarib tashlaydi (StockEntry.debt IS NULL)
      - 'all'  -> hammasi
    Returns: (totals: dict, source: str)
    """
    StockEntry = get_model('StockEntry')
    if not StockEntry:
        return {'quantity': 0, 'value_usd': D0}, 'none'

    kwargs = date_range_kwargs(StockEntry, date_from, date_to)  # created_at oralig'i
    qs = StockEntry.objects.filter(**kwargs)
    qs = try_filter_store(qs, store_id, ['product__store_id', 'product__store__id'])

    # unit_price USD ga normallashtirish (odatda allaqachon USD, lekin xavfsizlik uchun)
    if find_field(StockEntry, ['currency']) and find_field(StockEntry, ['exchange_rate']):
        unit_price_usd = as_usd('unit_price', 'currency', 'exchange_rate')
    else:
        unit_price_usd = ExpressionWrapper(F('unit_price'),
                            output_field=DecimalField(max_digits=20, decimal_places=6))

    qs = qs.annotate(line_value_usd=ExpressionWrapper(
        unit_price_usd * F('quantity'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    ))

    if mode == 'pure':
        qs_use = qs.filter(debt__isnull=True)
        src = "StockEntry (exclude debt-linked) unit_price normalized"
    else:
        qs_use = qs
        src = "StockEntry (all) unit_price normalized"

    quantity = qs_use.aggregate(v=Coalesce(Sum('quantity', output_field=IntegerField()), Value(0)))['v'] or 0
    value_usd = qs_use.aggregate(v=Coalesce(Sum('line_value_usd'), Value(D0),
                               output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0

    return {'quantity': quantity, 'value_usd': value_usd}, src
