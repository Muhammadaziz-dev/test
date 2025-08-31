
from decimal import Decimal
from django.apps import apps
from django.core.exceptions import FieldError
from django.db.models import DateField, DateTimeField

D0 = Decimal('0')


def get_model(name: str):
    for m in apps.get_models():
        if m.__name__ == name:
            return m
    return None


def find_field(model, candidates):
    if not model:
        return None
    names = {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}
    for c in candidates:
        if c in names:
            return c
    return None


def date_range_kwargs(Model, start_dt, end_dt):
    if not Model:
        return {}
    fields = {f.name: f for f in Model._meta.get_fields() if hasattr(f, "attname")}
    for cand in ("created_at", "date", "created", "datetime", "timestamp", "created_on"):
        f = fields.get(cand)
        if f:
            if isinstance(f, DateField) and not isinstance(f, DateTimeField):
                return {f"{cand}__range": (start_dt.date(), end_dt.date())}
            return {f"{cand}__range": (start_dt, end_dt)}
    return {}


def try_filter_store(qs, store_id, candidates):
    if not store_id:
        return qs
    for path in candidates:
        try:
            return qs.filter(**{path: store_id})
        except FieldError:
            continue
    return qs
```

---

## analytics/utils/money.py

```python
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
```

---

## analytics/utils/time\_range.py

```python
from datetime import datetime, timedelta
from django.utils import timezone


def parse_range(q):
    """date_from/date_to or period presets (daily/weekly/monthly/yearly/all)."""
    def parse_one(s, end=False):
        if not s:
            return None
        dt = datetime.fromisoformat(s)
        if len(s) == 10 and end:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt

    def start_of_week(dt):
        return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

    def month_bounds(dt):
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            next_start = start.replace(year=start.year + 1, month=1)
        else:
            next_start = start.replace(month=start.month + 1)
        end = next_start - timedelta(microseconds=1)
        return start, end

    def year_bounds(dt):
        start = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1) - timedelta(microseconds=1)
        return start, end

    tz = timezone.get_default_timezone()
    now = timezone.localtime()

    df_raw = parse_one(q.get('date_from'))
    dt_raw = parse_one(q.get('date_to'), end=True)
    period = (q.get('period') or q.get('range') or q.get('freq') or '').lower().strip()

    if df_raw or dt_raw:
        df = df_raw or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt = dt_raw or now
    elif period in {'daily', 'day'}:
        anchor = now
        df = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
        dt = anchor.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period in {'weekly', 'week'}:
        ws = start_of_week(now)
        df, dt = ws, ws + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    elif period in {'monthly', 'month'}:
        df, dt = month_bounds(now)
    elif period in {'yearly', 'year'}:
        df, dt = year_bounds(now)
    elif period in {'all', 'full'}:
        df, dt = datetime(1970, 1, 1), now
    else:
        df = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt = now

    # Anchor period to date_from if provided (and no explicit range used)
    if (not (df_raw or dt_raw)) and q.get('date_from') and period in {'daily','day','weekly','week','monthly','month','yearly','year'}:
        anchor = datetime.fromisoformat(q.get('date_from'))
        if timezone.is_naive(anchor):
            anchor = timezone.make_aware(anchor, tz)
        if period in {'daily','day'}:
            df = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
            dt = anchor.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period in {'weekly','week'}:
            ws = start_of_week(anchor)
            df, dt = ws, ws + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        elif period in {'monthly','month'}:
            df, dt = month_bounds(anchor)
        elif period in {'yearly','year'}:
            df, dt = year_bounds(anchor)

    if timezone.is_naive(df):
        df = timezone.make_aware(df, tz)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, tz)
    return df, dt
```

---

## analytics/selectors/turnover.py

```python
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
```

---

## analytics/selectors/gross\_profit.py

```python
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
```

---

## analytics/selectors/expenses.py

```python
from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_opex(date_from, date_to, store_id=None):
    Expense = get_model('Expense')
    if Expense:
        kwargs_e = date_range_kwargs(Expense, date_from, date_to)
        qs_e = try_filter_store(Expense.objects.filter(**kwargs_e), store_id, ['store_id', 'cashbox__store_id', 'store__id'])
        if find_field(Expense, ['currency']) and find_field(Expense, ['exchange_rate']):
            qs_e = qs_e.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
            v = qs_e.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
            return v or D0, 'Expense.amount (normalized)'
        v = qs_e.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
        return v or D0, 'Expense.amount'

    CashTransaction = get_model('CashTransaction')
    if CashTransaction:
        kwargs_c = date_range_kwargs(CashTransaction, date_from, date_to)
        qs_c = try_filter_store(CashTransaction.objects.filter(type='EXPENSE', **kwargs_c), store_id, ['store_id', 'cashbox__store_id', 'store__id'])
        if find_field(CashTransaction, ['currency']) and find_field(CashTransaction, ['exchange_rate']):
            qs_c = qs_c.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
            v = qs_c.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
            return v or D0, 'CashTransaction.EXPENSE (normalized)'
        v = qs_c.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
        return v or D0, 'CashTransaction.EXPENSE'

    return D0, 'none'
```

---

## analytics/selectors/salaries.py

```python
from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_salaries(date_from, date_to, store_id=None):
    SalaryPayment = get_model('SalaryPayment')
    if not SalaryPayment:
        return D0, 'none'
    kwargs_s = date_range_kwargs(SalaryPayment, date_from, date_to)
    qs_s = try_filter_store(SalaryPayment.objects.filter(**kwargs_s), store_id, ['store_id', 'employee__store_id', 'store__id'])
    if find_field(SalaryPayment, ['currency']) and find_field(SalaryPayment, ['exchange_rate']):
        qs_s = qs_s.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
        v = qs_s.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
        return v or D0, 'SalaryPayment.amount (normalized)'
    v = qs_s.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
    return v or D0, 'SalaryPayment.amount'
```

---

## analytics/selectors/outflows.py

```python
from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_total_outflows(date_from, date_to, store_id, opex, salaries, mode='ops+salary', extra_types=None):
    total = (opex or D0) + (salaries or D0)
    source_parts = ['operating_expenses', 'salaries']

    if mode == 'all':
        CashTransaction = get_model('CashTransaction')
        if CashTransaction:
            kwargs_co = date_range_kwargs(CashTransaction, date_from, date_to)
            qs_co = try_filter_store(CashTransaction.objects.filter(**kwargs_co), store_id, ['store_id', 'cashbox__store_id', 'store__id'])
            tfield = find_field(CashTransaction, ['type'])
            if tfield:
                default_types = ['PURCHASE', 'SUPPLIER_PAYMENT', 'TAX', 'LOAN_REPAYMENT', 'WITHDRAWAL', 'OTHER_OUT']
                types = [t.strip().upper() for t in (extra_types or default_types)]
                qs_co = qs_co.filter(**{f"{tfield}__in": types})
            if find_field(CashTransaction, ['currency']) and find_field(CashTransaction, ['exchange_rate']):
                qs_co = qs_co.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
                extra = qs_co.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            else:
                extra = qs_co.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            total += extra
            source_parts.append('CashTransaction[extra_outflows]')

    return total, '+'.join(source_parts)
```

---

## analytics/services/net\_profit.py

```python
from decimal import Decimal
from . import __init__  # noqa
from ..selectors.turnover import compute_turnover
from ..selectors.gross_profit import compute_gross_profit
from ..selectors.expenses import compute_opex
from ..selectors.salaries import compute_salaries
from ..selectors.outflows import compute_total_outflows

D0 = Decimal('0')


def compute(date_from, date_to, store_id=None, *, turnover_mode='sales', outflow_mode='ops+salary', out_types=None):
    turnover, t_src = compute_turnover(date_from, date_to, store_id, mode=turnover_mode)
    gross, g_src = compute_gross_profit(date_from, date_to, store_id)
    opex, e_src = compute_opex(date_from, date_to, store_id)
    salaries, s_src = compute_salaries(date_from, date_to, store_id)
    total_out, out_src = compute_total_outflows(date_from, date_to, store_id, opex, salaries, mode=outflow_mode, extra_types=out_types)
    net = (gross or D0) - (opex or D0) - (salaries or D0)

    return {
        'turnover_usd': turnover,
        'gross_profit_usd': gross,
        'operating_expenses_usd': opex,
        'salaries_usd': salaries,
        'total_outflows_usd': total_out,
        'net_profit_usd': net,
        'sources': {
            'turnover': t_src,
            'sales': g_src,
            'expenses': e_src,
            'salaries': s_src,
            'outflows': out_src,
        }
    }
```

---

## analytics/views.py (yangilangan)

```python
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .utils.time_range import parse_range
from .services.net_profit import compute as compute_net


class AnalyticsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='net-profit')
    def net_profit(self, request, *args, **kwargs):
        store_id = kwargs.get('store_id')
        date_from, date_to = parse_range(request.query_params)

        turnover_mode = (request.query_params.get('turnover') or 'sales').lower()
        outflow_mode = (request.query_params.get('outflow') or 'ops+salary').lower()
        out_types_param = request.query_params.get('out_types')
        out_types = [t.strip().upper() for t in out_types_param.split(',')] if out_types_param else None

        result = compute_net(
            date_from, date_to, store_id,
            turnover_mode=turnover_mode,
            outflow_mode=outflow_mode,
            out_types=out_types,
        )

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'turnover_mode': turnover_mode,
            'outflow_mode': outflow_mode,
            **result,
        })
```

---

### urls.py (o‘zgarmaydi)

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AnalyticsViewSet

router = DefaultRouter()
router.register(r'', AnalyticsViewSet, basename='analytics')
urlpatterns = router.urls
```

---

### Qisqa yo‘riqnoma

# 1. Fayllarni ko‘rsatilgan yo‘llarga qo‘ying.
# 2. `analytics/views.py` ni shu versiyaga yangilang.
# 3. Serverni ishga tushiring va tekshiring:

#    * `/platform/1/analytics/net-profit/?period=weekly`
#    * `/platform/1/analytics/net-profit/?date_from=2025-08-01&date_to=2025-08-20&turnover=all&outflow=all`
