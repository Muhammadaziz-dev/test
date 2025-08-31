# analytics/services/cash.py
from decimal import Decimal
from typing import Literal, List, Dict, Any, Optional

from django.db.models import Sum, Count, Case, When, Value, CharField, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

from cashbox.models import Cashbox, CashTransaction

Interval = Literal["day", "week", "month"]
TRUNC = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}

SOURCE_CASE = Case(
    When(order__isnull=False, then=Value("order")),
    When(expense__isnull=False, then=Value("expense")),
    When(entry_system__isnull=False, then=Value("entry_system")),
    When(debt_document__isnull=False, then=Value("debt")),
    When(~Q(manual_source=""), then=Value("manual")),
    default=Value("other"),
    output_field=CharField(),
)


def _get_cashbox(store_id: int) -> Optional[Cashbox]:
    try:
        return Cashbox.objects.select_related("store").get(store_id=store_id)
    except Cashbox.DoesNotExist:
        return None


def cash_metrics(store_id: int, start, end) -> Dict[str, Any]:
    cb = _get_cashbox(store_id)

    if not cb:
        return {
            "recorded_balance": Decimal("0"),
            "recalculated_balance": Decimal("0"),
            "discrepancy": Decimal("0"),
            "inflow": Decimal("0"),
            "outflow": Decimal("0"),
            "net_flow": Decimal("0"),
            "inflow_count": 0,
            "outflow_count": 0,
            "first_tx_date": None,
        }

    base = CashTransaction.objects.filter(cashbox=cb)

    # Auditorlik: barcha tarix bo‘yicha qayta hisoblangan balans
    agg_all = base.aggregate(
        inflow=Sum("amount", filter=Q(is_out=False)) or Decimal("0"),
        outflow=Sum("amount", filter=Q(is_out=True)) or Decimal("0"),
    )
    recalculated = (agg_all["inflow"] or Decimal("0")) - (agg_all["outflow"] or Decimal("0"))

    # Davr bo‘yicha oqimlar
    in_period = base.filter(created_at__gte=start, created_at__lt=end)
    agg = in_period.aggregate(
        inflow=Sum("amount", filter=Q(is_out=False)),
        outflow=Sum("amount", filter=Q(is_out=True)),
        inflow_count=Count("id", filter=Q(is_out=False)),
        outflow_count=Count("id", filter=Q(is_out=True)),
    )

    inflow = agg["inflow"] or Decimal("0")
    outflow = agg["outflow"] or Decimal("0")

    first_tx = base.order_by("created_at").values_list("created_at", flat=True).first()

    return {
        "recorded_balance": cb.balance,
        "recalculated_balance": recalculated,
        "discrepancy": (cb.balance or Decimal("0")) - (recalculated or Decimal("0")),
        "inflow": inflow,
        "outflow": outflow,
        "net_flow": inflow - outflow,
        "inflow_count": agg["inflow_count"] or 0,
        "outflow_count": agg["outflow_count"] or 0,
        "first_tx_date": first_tx,
    }


def cash_timeseries(store_id: int, start, end, interval: Interval = "day") -> List[Dict[str, Any]]:
    cb = _get_cashbox(store_id)
    if not cb:
        return []

    trunc = TRUNC[interval]
    qs = (
        CashTransaction.objects
        .filter(cashbox=cb, created_at__gte=start, created_at__lt=end)
        .annotate(ts=trunc("created_at"))
        .values("ts")
        .annotate(
            inflow=Sum("amount", filter=Q(is_out=False)),
            outflow=Sum("amount", filter=Q(is_out=True)),
            tx_count=Count("id"),
        )
        .order_by("ts")
    )
    data = []
    for r in qs:
        inflow = r["inflow"] or Decimal("0")
    outflow = r["outflow"] or Decimal("0")
    data.append({
        "ts": r["ts"],
        "inflow": inflow,
        "outflow": outflow,
        "net": inflow - outflow,
        "tx_count": r["tx_count"],
    })
    return data


def cash_breakdown_by_source(store_id: int, start, end, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    cb = _get_cashbox(store_id)
    if not cb:
        return []

    qs = (
        CashTransaction.objects
        .filter(cashbox=cb, created_at__gte=start, created_at__lt=end)
        .annotate(source=SOURCE_CASE)
        .values("source")
        .annotate(
            inflow=Sum("amount", filter=Q(is_out=False)),
            outflow=Sum("amount", filter=Q(is_out=True)),
            count=Count("id"),
        )
    )

    data = []

    for r in qs:
        inflow = r["inflow"] or Decimal("0")
        outflow = r["outflow"] or Decimal("0")
        data.append({
            "source": r["source"],
            "inflow": inflow,
            "outflow": outflow,
            "net": inflow - outflow,
            "count": r["count"],
        })

    data.sort(key=lambda x: (x["inflow"] + x["outflow"]), reverse=True)
    return data[:limit] if (limit and limit > 0) else data


def recent_transactions(store_id: int, start, end, limit: int = 20) -> List[Dict[str, Any]]:
    cb = _get_cashbox(store_id)
    if not cb:
        return []

    qs = (
        CashTransaction.objects
        .filter(cashbox=cb, created_at__gte=start, created_at__lt=end)
        .select_related("order", "expense", "entry_system", "debt_document")
        .order_by("-created_at")[:limit]
    )

    items = []
    for t in qs:
        if t.order_id:
            src = "order"
            label = f"Order #{t.order_id}"
        elif t.expense_id:
            src = "expense"
            label = "Expense"
        elif t.entry_system_id:
            src = "entry_system"
            label = f"EntrySystem #{t.entry_system_id}"
        elif t.debt_document_id:
            src = "debt"
            label = f"Debt #{t.debt_document_id}"
        elif t.manual_source:
            src = "manual"
            label = t.manual_source
        elif t.note:
            src = "note"
            label = t.note
        else:
            src = "other"
            label = "Unknown"

    items.append({
        "id": t.id,
        "created_at": t.created_at,
        "amount": t.amount,
        "direction": "out" if t.is_out else "in",
        "source": src,
        "label": label,
    })
    return items


def largest_transactions(store_id: int, start, end, limit: int = 10) -> List[Dict[str, Any]]:
    cb = _get_cashbox(store_id)
    if not cb:
        return []

    qs = (
        CashTransaction.objects
        .filter(cashbox=cb, created_at__gte=start, created_at__lt=end)
        .order_by("-amount")[:limit]
    )
    return [
        {
            "id": t.id,
            "created_at": t.created_at,
            "amount": t.amount,
            "direction": "out" if t.is_out else "in",
        }
        for t in qs
    ]
