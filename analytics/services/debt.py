from decimal import Decimal
from typing import Literal, List, Dict, Any, Optional

from django.db.models import Sum, Count, Case, When, Value, Q, F, DecimalField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, Coalesce
from django.db.models import ExpressionWrapper as EW
from django.utils import timezone

from loan.models import DebtUser, DebtDocument

Interval = Literal["day", "week", "month"]
TRUNC = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}


DOC_BASE = lambda store_id, start, end, include_mirror=False: (
    DebtDocument.objects
    .filter(store_id=store_id, date__gte=start, date__lt=end, is_deleted=False)
    .filter(Q(is_mirror=False) | Q(is_mirror=True) if include_mirror else Q(is_mirror=False))
)

TOTAL_USD = lambda: EW(
    Case(
        When(currency='UZS', then=F('total_amount') / F('exchange_rate')),
        default=F('total_amount'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    ),
    output_field=DecimalField(max_digits=20, decimal_places=6)
)

CASH_USD = lambda: EW(
    Case(
        When(currency='UZS', then=F('cash_amount') / F('exchange_rate')),
        default=F('cash_amount'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    ),
    output_field=DecimalField(max_digits=20, decimal_places=6)
)

PROD_USD = lambda: EW(
    Case(
        When(currency='UZS', then=F('product_amount') / F('exchange_rate')),
        default=F('product_amount'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    ),
    output_field=DecimalField(max_digits=20, decimal_places=6)
)

BALANCE_USD = lambda: EW(
    Case(
        When(currency='UZS', then=F('balance') / F('exchange_rate')),
        default=F('balance'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    ),
    output_field=DecimalField(max_digits=20, decimal_places=6)
)



def debt_metrics(store_id: int, start, end, include_mirror: bool = False) -> Dict[str, Any]:
    docs = DOC_BASE(store_id, start, end, include_mirror)

    agg = docs.aggregate(
        transferred=Sum(TOTAL_USD(), filter=Q(method='transfer')),
        accepted=Sum(TOTAL_USD(), filter=Q(method='accept')),
        cash_transferred=Sum(CASH_USD(), filter=Q(method='transfer')),
        cash_accepted=Sum(CASH_USD(), filter=Q(method='accept')),
        prod_transferred=Sum(PROD_USD(), filter=Q(method='transfer')),
        prod_accepted=Sum(PROD_USD(), filter=Q(method='accept')),
        transfer_count=Count('id', filter=Q(method='transfer')),
        accept_count=Count('id', filter=Q(method='accept')),
    )

    transferred = agg['transferred'] or Decimal('0')
    accepted = agg['accepted'] or Decimal('0')
    net = transferred - accepted

    du_qs = DebtUser.objects.filter(store_id=store_id)
    du_agg = du_qs.aggregate(
        outstanding_usd=Sum(BALANCE_USD(), filter=Q(balance__gt=0)),
        debtors=Count('id', filter=Q(balance__gt=0)),
    )

    return {
        'transferred_usd': transferred,
        'accepted_usd': accepted,
        'net_flow_usd': net,
        'transfer_count': agg['transfer_count'] or 0,
        'accept_count': agg['accept_count'] or 0,
        'cash': {
            'transferred_usd': agg['cash_transferred'] or Decimal('0'),
            'accepted_usd': agg['cash_accepted'] or Decimal('0'),
        },
        'product': {
            'transferred_usd': agg['prod_transferred'] or Decimal('0'),
            'accepted_usd': agg['prod_accepted'] or Decimal('0'),
        },
        'outstanding_usd': du_agg['outstanding_usd'] or Decimal('0'),
        'active_debtors': du_agg['debtors'] or 0,
        'repayment_rate': (accepted / transferred) if transferred else Decimal('0'),
    }


# --- Time series ---

def debt_timeseries(store_id: int, start, end, interval: Interval = 'day', include_mirror: bool = False) -> List[Dict[str, Any]]:
    trunc = TRUNC[interval]
    docs = DOC_BASE(store_id, start, end, include_mirror).annotate(ts=trunc('date'))

    qs = (
        docs.values('ts')
        .annotate(
            transferred=Sum(TOTAL_USD(), filter=Q(method='transfer')),
            accepted=Sum(TOTAL_USD(), filter=Q(method='accept')),
            tx_count=Count('id'),
        )
        .order_by('ts')
    )

    data = []
    for r in qs:
        t = r['transferred'] or Decimal('0')
        a = r['accepted'] or Decimal('0')
        data.append({'ts': r['ts'], 'transferred_usd': t, 'accepted_usd': a, 'net_usd': t - a, 'tx_count': r['tx_count']})
    return data


# --- Top debtors ---

def top_debtors(store_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    from django.db.models import Max
    du = (DebtUser.objects
          .filter(store_id=store_id)
          .annotate(balance_usd=BALANCE_USD(), last_activity=Max('documents__date'))
          .filter(balance__gt=0)
          .order_by('-balance_usd')[:limit])

    return [
        {
            'id': d.id,
            'phone_number': d.phone_number,
            'first_name': d.first_name,
            'last_name': d.last_name,
            'balance': d.balance,
            'currency': d.currency,
            'exchange_rate': d.exchange_rate,
            'balance_usd': d.balance_usd,
            'last_activity': d.last_activity,
        }
        for d in du
    ]


# --- Ageing (balansning yoshi) ---

def debt_ageing(store_id: int, as_of, buckets: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Buckets: [7, 30, 60, 90] => 0-7, 8-30, 31-60, 61-90, 90+
    Asos: debtor’ning oxirgi faoliyati (so‘nggi hujjat sanasi) va hozirgi balans.
    """
    from django.db.models import Max

    if not buckets:
        buckets = [7, 30, 60, 90]

    du = (DebtUser.objects
          .filter(store_id=store_id)
          .annotate(balance_usd=BALANCE_USD(), last_activity=Max('documents__date'))
          .filter(balance__gt=0))

    now = as_of
    ranges = [(0, buckets[0]), (buckets[0]+1, buckets[1]), (buckets[1]+1, buckets[2]), (buckets[2]+1, buckets[3]), (buckets[3]+1, 99999)]
    labels = [f"0-{buckets[0]}", f"{buckets[0]+1}-{buckets[1]}", f"{buckets[1]+1}-{buckets[2]}", f"{buckets[2]+1}-{buckets[3]}", f">{buckets[3]}"]

    init = [{'label': labels[i], 'debtors': 0, 'outstanding_usd': Decimal('0')} for i in range(len(labels))]

    for d in du:
        last = d.last_activity or d.created_at
        days = (now - last).days if last else 99999
        bal = d.balance_usd or Decimal('0')

        idx = 4
        for i, (lo, hi) in enumerate(ranges):
            if lo <= days <= hi:
                idx = i
                break
        init[idx]['debtors'] += 1
        init[idx]['outstanding_usd'] += bal

    return init


def debt_breakdown(store_id: int, start, end, include_mirror: bool = False) -> Dict[str, Any]:
    docs = DOC_BASE(store_id, start, end, include_mirror)

    def agg_for(method: str):
        sub = docs.filter(method=method)
        a = sub.aggregate(
            total_usd=Sum(TOTAL_USD()),
            cash_usd=Sum(CASH_USD()),
            product_usd=Sum(PROD_USD()),
            count=Count('id')
        )
        return {
            'total_usd': a['total_usd'] or Decimal('0'),
            'cash_usd': a['cash_usd'] or Decimal('0'),
            'product_usd': a['product_usd'] or Decimal('0'),
            'count': a['count'] or 0,
        }

    return {
        'transfer': agg_for('transfer'),
        'accept': agg_for('accept'),
    }


def recent_debt_documents(store_id: int, start, end, limit: int = 20, include_mirror: bool = False) -> List[Dict[str, Any]]:
    qs = (DOC_BASE(store_id, start, end, include_mirror)
          .select_related('debtuser')
          .order_by('-date')[:limit])

    items = []
    for d in qs:
        items.append({
            'id': d.id,
            'date': d.date,
            'method': d.method,
            'currency': d.currency,
            'exchange_rate': d.exchange_rate,
            'cash_amount': d.cash_amount,
            'product_amount': d.product_amount,
            'total_amount': d.total_amount,
            'total_usd': (d.total_amount / d.exchange_rate if d.currency == 'UZS' else d.total_amount),
            'phone_number': d.phone_number or (d.debtuser.phone_number if d.debtuser else None),
            'name': (
                f"{(d.first_name or (d.debtuser.first_name if d.debtuser else ''))} "
                f"{(d.last_name or (d.debtuser.last_name if d.debtuser else ''))}"
            ).strip(),
        })
    return items