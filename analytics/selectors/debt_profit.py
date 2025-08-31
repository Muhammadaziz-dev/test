from decimal import Decimal
from django.db.models import (
    Sum, Value, F, DecimalField, ExpressionWrapper, Case, When
)
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0
from .turnover import compute_turnover
from .gross_profit import compute_gross_profit
from .debts import compute_debts

def _sum_usd_qs(qs, field_name, currency='currency', rate='exchange_rate'):
    Model = qs.model
    if find_field(Model, [currency]) and find_field(Model, [rate]):
        qs = qs.annotate(val_usd=as_usd(field_name, currency, rate))
        return qs.aggregate(
            v=Coalesce(Sum('val_usd'), Value(D0),
                       output_field=DecimalField(max_digits=20, decimal_places=6))
        )['v'] or D0
    return qs.aggregate(
        v=Coalesce(Sum(field_name), Value(D0),
                   output_field=DecimalField(max_digits=20, decimal_places=6))
    )['v'] or D0

def _sum(qs, field_name):
    return qs.aggregate(
        v=Coalesce(Sum(field_name), Value(D0),
                   output_field=DecimalField(max_digits=20, decimal_places=6))
    )['v'] or D0

def _docs_profit(date_from, date_to, store_id=None, upto=False):
    DebtDocument = get_model('DebtDocument')
    DocumentProduct = get_model('DocumentProduct')
    Product = get_model('Product')
    if not (DebtDocument and DocumentProduct):
        return None

    # 1) Hujjatlar oynasi
    if upto:
        kwargs_docs = date_range_kwargs(DebtDocument, date_from.replace(year=1970, month=1, day=1), date_to)
    else:
        kwargs_docs = date_range_kwargs(DebtDocument, date_from, date_to)

    docs = DebtDocument.objects.filter(**kwargs_docs, is_deleted=False, method='transfer')
    docs = try_filter_store(docs, store_id, ['store_id', 'store__id'])

    # 2) Liniyalar (faqat transfer hujjatlar)
    lines = DocumentProduct.objects.filter(document__in=docs)

    # revenue_usd
    has_fx_line = find_field(DocumentProduct, ['currency']) and find_field(DocumentProduct, ['exchange_rate'])
    price_usd = as_usd('price', 'currency', 'exchange_rate') if has_fx_line else ExpressionWrapper(
        F('price'), output_field=DecimalField(max_digits=20, decimal_places=6)
    )
    lines = lines.annotate(
        revenue_usd=ExpressionWrapper(price_usd * F('quantity'),
                                      output_field=DecimalField(max_digits=20, decimal_places=6))
    )

    # cogs_usd = product__avg_cost * qty
    avg_cost_name = None
    if Product:
        for cand in ['average_cost_usd', 'avg_cost_usd', 'average_cost', 'avg_cost',
                     'cost_price', 'purchase_price', 'unit_cost_usd']:
            if find_field(Product, [cand]):
                avg_cost_name = cand
                break
    if avg_cost_name:
        lines = lines.annotate(
            cogs_usd=ExpressionWrapper(F(f'product__{avg_cost_name}') * F('quantity'),
                                       output_field=DecimalField(max_digits=20, decimal_places=6))
        )
    else:
        lines = lines.annotate(cogs_usd=Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))

    lines = lines.annotate(
        gp_usd=ExpressionWrapper(F('revenue_usd') - F('cogs_usd'),
                                 output_field=DecimalField(max_digits=20, decimal_places=6))
    )
    gp_total = lines.aggregate(v=Coalesce(Sum('gp_usd'), Value(D0),
                              output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0

    if upto:
        # ratio = max( Σtransfer(total - income) − Σaccept(total), 0 ) / Σtransfer(total)
        transfers_all = try_filter_store(
            DebtDocument.objects.filter(**kwargs_docs, is_deleted=False, method='transfer'),
            store_id, ['store_id', 'store__id']
        )
        accepts_all = try_filter_store(
            DebtDocument.objects.filter(**kwargs_docs, is_deleted=False, method='accept'),
            store_id, ['store_id', 'store__id']
        )

        # USD normalize
        t_total = _sum_usd_qs(transfers_all, 'total_amount', 'currency', 'exchange_rate')
        t_income = _sum_usd_qs(transfers_all, 'income', 'currency', 'exchange_rate') if find_field(DebtDocument, ['income']) else D0
        a_total = _sum_usd_qs(accepts_all, 'total_amount', 'currency', 'exchange_rate')

        unpaid = (t_total - t_income) - a_total
        if unpaid < D0:
            unpaid = D0

        ratio = (unpaid / t_total) if t_total and t_total != D0 else D0
        recv_profit = gp_total * ratio if ratio else D0

        return {
            'gp': gp_total,
            'recv_profit': recv_profit,
            'sources': {
                'gp': 'DebtDocument.transfer → Σ(DocumentProduct.(price*qty − avg_cost*qty))',
                'recv_profit': 'GP_total × ( (Σtransfer(total−income)−Σaccept(total)) / Σtransfer(total) )',
                'avg_cost_field': avg_cost_name or 'none',
                'strategy': 'debt_docs_products'
            }
        }

    # upto=False
    return {
        'gp': gp_total,
        'recv_profit': None,
        'sources': {
            'gp': 'DebtDocument.transfer → Σ(DocumentProduct.(price*qty − avg_cost*qty))',
            'avg_cost_field': avg_cost_name or 'none',
            'strategy': 'debt_docs_products'
        }
    }

def _orders_prorated_profit(date_from, date_to, store_id=None, upto=False):
    """
    Order.total_profit × unpaid_ratio (aniq prorat­siya).
    """
    Order = get_model('Order')
    if not Order:
        return None

    if upto:
        kwargs_o = date_range_kwargs(Order, date_from.replace(year=1970, month=1, day=1), date_to)
    else:
        kwargs_o = date_range_kwargs(Order, date_from, date_to)

    qs = Order.objects.filter(**kwargs_o)
    qs = try_filter_store(qs, store_id, ['store_id', 'store__id'])

    for flag in ['is_deleted', 'deleted', 'is_canceled', 'is_cancelled']:
        if find_field(Order, [flag]):
            qs = qs.filter(**{flag: False})
            break

    price_field = find_field(Order, ['total_price', 'amount', 'sum'])
    paid_field = find_field(Order, ['paid_amount', 'paid', 'payment', 'paid_sum'])
    profit_field = find_field(Order, ['total_profit', 'profit'])
    if not (price_field and profit_field):
        return None

    has_fx = find_field(Order, ['currency']) and find_field(Order, ['exchange_rate'])

    price_usd = as_usd(price_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(price_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    paid_usd = as_usd(paid_field, 'currency', 'exchange_rate') if (has_fx and paid_field) else \
        (ExpressionWrapper(F(paid_field), output_field=DecimalField(max_digits=20, decimal_places=6))
         if paid_field else Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))
    profit_usd = as_usd(profit_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(profit_field), output_field=DecimalField(max_digits=20, decimal_places=6))

    qs = qs.annotate(_diff=ExpressionWrapper(price_usd - paid_usd,
                                             output_field=DecimalField(max_digits=20, decimal_places=6)))
    qs = qs.annotate(unpaid_usd=Case(
        When(_diff__gt=Value(D0), then=F('_diff')),
        default=Value(D0),
        output_field=DecimalField(max_digits=20, decimal_places=6),
    ))
    qs = qs.annotate(unpaid_ratio=Case(
        When(**{f"{price_field}__gt": 0}, then=ExpressionWrapper(
            F('unpaid_usd') / price_usd,
            output_field=DecimalField(max_digits=20, decimal_places=6)
        )),
        default=Value(D0),
        output_field=DecimalField(max_digits=20, decimal_places=6),
    ))
    qs = qs.annotate(prorated_profit_usd=ExpressionWrapper(
        profit_usd * F('unpaid_ratio'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    ))

    return {
        'gp': _sum(qs, 'prorated_profit_usd'),
        'recv_profit': None if not upto else _sum(qs, 'prorated_profit_usd'),
        'sources': {
            'gp': 'Order.total_profit × unpaid_ratio',
            'strategy': 'orders_prorated'
        }
    }


def compute_debt_profit(date_from, date_to, store_id=None, debts_source='auto'):
    """
    Qaytaradi:
      debt_profit_usd        - davr ichidagi kredit sotuvlardagi foyda
      receivables_profit_usd - date_to holatidagi qoldiq qarz ichidagi foyda
      sources                - ishlatilgan strategiya/manbalar
    Strategiya ustuvorligi:
      1) debts_source='docs' yoki ('auto' va DebtDocument mavjud) => DebtDocument/Product asosida
      2) Aks holda: Order prorat­siya
      3) Agar ikkisi ham imkonsiz: margin-rate fallback (taxmin)
    """
    DebtDocument = get_model('DebtDocument')
    use_docs = (debts_source == 'docs') or (debts_source == 'auto' and DebtDocument is not None)

    # 1) DebtDocument/Product asosida
    if use_docs and DebtDocument:
        now_gp = _docs_profit(date_from, date_to, store_id, upto=False)
        upto_gp = _docs_profit(date_from, date_to, store_id, upto=True)
        if now_gp and upto_gp:
            return {
                'debt_profit_usd': now_gp['gp'],
                'receivables_profit_usd': upto_gp['recv_profit'] or D0,
                'sources': {
                    'debt_profit': now_gp['sources']['gp'],
                    'receivables_profit': upto_gp['sources']['recv_profit'],
                    'strategy': now_gp['sources']['strategy'],
                    'avg_cost_field': now_gp['sources'].get('avg_cost_field')
                }
            }

    # 2) Order prorat­siya
    ord_now = _orders_prorated_profit(date_from, date_to, store_id, upto=False)
    ord_upto = _orders_prorated_profit(date_from, date_to, store_id, upto=True)
    if ord_now and ord_upto:
        return {
            'debt_profit_usd': ord_now['gp'],
            'receivables_profit_usd': ord_upto['recv_profit'] or D0,
            'sources': {
                'debt_profit': ord_now['sources']['gp'],
                'receivables_profit': 'Order.total_profit × unpaid_ratio (upto date_to)',
                'strategy': ord_now['sources']['strategy']
            }
        }

    # 3) Margin-rate fallback: (gross_profit/turnover) × debt metrics
    turnover, _ = compute_turnover(date_from, date_to, store_id, mode='sales')
    gross, _ = compute_gross_profit(date_from, date_to, store_id)
    margin_rate = (gross / turnover) if turnover and turnover != D0 else Decimal('0')

    debts = compute_debts(date_from, date_to, store_id, source=debts_source)
    debt_given = debts.get('debt_given_usd') or D0
    recv_out = debts.get('receivables_outstanding_usd') or D0

    return {
        'debt_profit_usd': (debt_given * margin_rate) if margin_rate else D0,
        'receivables_profit_usd': (recv_out * margin_rate) if margin_rate else D0,
        'sources': {
            'debt_profit': 'estimate: margin_rate × debt_given',
            'receivables_profit': 'estimate: margin_rate × receivables_outstanding',
            'strategy': 'margin_rate_fallback',
            'margin_rate': float(margin_rate) if margin_rate else 0.0
        }
    }
