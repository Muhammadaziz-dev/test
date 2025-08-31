from datetime import timedelta
from django.db.models import (
    Sum, Count, Value, F, DecimalField, ExpressionWrapper, Case, When, DateTimeField
)
from django.db.models.functions import Coalesce, TruncDay, TruncWeek, TruncMonth, TruncYear
from django.utils import timezone

from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def _choose_trunc(granularity: str):
    g = (granularity or 'auto').lower()
    if g in ('day', 'daily'):     return TruncDay,   'day'
    if g in ('week', 'weekly'):   return TruncWeek,  'week'
    if g in ('month', 'monthly'): return TruncMonth, 'month'
    if g in ('year', 'yearly'):   return TruncYear,  'year'
    return None, 'auto'


def _auto_granularity(date_from, date_to):
    days = (date_to - date_from).days + 1
    if days <= 31:   return 'day'
    if days <= 180:  return 'week'
    if days <= 800:  return 'month'
    return 'year'


def _align_start(dt, gnorm):
    # granularity bo‘yicha period start’ini tekislaymiz
    if gnorm == 'day':
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if gnorm == 'week':
        ws = dt - timedelta(days=dt.weekday())  # dushanba
        return ws.replace(hour=0, minute=0, second=0, microsecond=0)
    if gnorm == 'month':
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if gnorm == 'year':
        return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt


def _step(dt, gnorm):
    if gnorm == 'day':
        return dt + timedelta(days=1)
    if gnorm == 'week':
        return dt + timedelta(days=7)
    if gnorm == 'month':
        year = dt.year + (1 if dt.month == 12 else 0)
        month = 1 if dt.month == 12 else dt.month + 1
        return dt.replace(year=year, month=month)
    if gnorm == 'year':
        return dt.replace(year=dt.year + 1)
    return dt + timedelta(days=1)


def _bucket_key(dt, gnorm):
    # dict kalitlari uchun normalize qilingan kalit
    d = dt.date()
    if gnorm == 'day' or gnorm == 'week':
        return d
    if gnorm == 'month':
        return d.replace(day=1)
    if gnorm == 'year':
        return d.replace(month=1, day=1)
    return d


def _normalize_orders_qs(Order, date_from, date_to, store_id):
    kwargs_o = date_range_kwargs(Order, date_from, date_to)
    qs = Order.objects.filter(**kwargs_o)
    qs = try_filter_store(qs, store_id, ['store_id', 'store__id'])

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
    return qs


def compute_orders_series(date_from, date_to, store_id=None, *, granularity='auto', fill_gaps=True):
    """
    Time-bucketed metrics for Orders:
      - orders_count, revenue_usd, profit_usd, inflow_usd, unpaid_sum_usd
    granularity: day|week|month|year|auto
    fill_gaps: timeline ichida bo‘sh bucket’larni 0-lar bilan to‘ldirish
    """
    Order = get_model('Order')
    if not Order:
        return {'granularity': granularity, 'series': [], 'source': 'Order not found'}

    if granularity == 'auto':
        granularity = _auto_granularity(date_from, date_to)

    trunc_cls, gnorm = _choose_trunc(granularity)
    if trunc_cls is None:
        trunc_cls, gnorm = TruncDay, 'day'

    qs = _normalize_orders_qs(Order, date_from, date_to, store_id)

    tz = timezone.get_current_timezone()
    bucket = trunc_cls('created_at', tzinfo=tz, output_field=DateTimeField())

    grouped = qs.annotate(bucket=bucket).values('bucket').annotate(
        orders_count=Coalesce(Count('id'), Value(0)),
        revenue_usd=Coalesce(Sum('_price_usd'),   Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        profit_usd=Coalesce(Sum('_profit_usd'),   Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        inflow_usd=Coalesce(Sum('_inflow_usd'),   Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        unpaid_sum_usd=Coalesce(Sum('unpaid_usd'),Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
    ).order_by('bucket')

    rows = list(grouped)

    # ---- fill gaps: ALWAYS from aligned period start ----
    if fill_gaps:
        start = _align_start(date_from, gnorm)
        end   = date_to  # period oxiri (bucket startlari end’dan oshmasa bo‘ldi)

        # mavjud qatorlarni tez topish uchun xarita
        m = {}
        for r in rows:
            key = _bucket_key(r['bucket'], gnorm)
            m[key] = r

        out = []
        cur = start
        while cur <= end:
            key = _bucket_key(cur, gnorm)
            rec = m.get(key)
            if rec:
                out.append({
                    'bucket': rec['bucket'],
                    'orders_count': rec['orders_count'],
                    'revenue_usd': rec['revenue_usd'],
                    'profit_usd': rec['profit_usd'],
                    'inflow_usd': rec['inflow_usd'],
                    'unpaid_sum_usd': rec['unpaid_sum_usd'],
                })
            else:
                out.append({
                    'bucket': cur,
                    'orders_count': 0,
                    'revenue_usd': D0,
                    'profit_usd': D0,
                    'inflow_usd': D0,
                    'unpaid_sum_usd': D0,
                })
            cur = _step(cur, gnorm)

        rows = out

    # Render: bucket -> ISO date
    series = []
    for r in rows:
        dt = r['bucket']
        series.append({
            'date': dt.date().isoformat(),
            'orders_count': int(r['orders_count'] or 0),
            'revenue_usd': r['revenue_usd'] or D0,
            'profit_usd': r['profit_usd'] or D0,
            'inflow_usd': r['inflow_usd'] or D0,
            'unpaid_sum_usd': r['unpaid_sum_usd'] or D0,
        })

    return {
        'granularity': gnorm,
        'series': series,
        'source': f'Order time-bucketed via {gnorm}; normalized to USD'
    }
