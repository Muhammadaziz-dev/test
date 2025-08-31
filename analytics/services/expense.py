# analytics/services/expense.py
from decimal import Decimal
from typing import Literal, List, Dict, Any, Optional

from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

from expense.models import Expense, EXPENSE_REASONS

Interval = Literal["day", "week", "month"]

TRUNC = {
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
}

REASON_LABELS = dict(EXPENSE_REASONS)


def expense_metrics(store_id: int, start, end) -> Dict[str, Any]:
    qs = Expense.objects.filter(
        store_id=store_id,
        is_deleted=False,
        date__gte=start,
        date__lt=end,
    )
    agg = qs.aggregate(total=Sum("amount"), cnt=Count("id"))
    total = agg["total"] or Decimal("0")
    cnt = agg["cnt"] or 0
    days = max((end - start).days, 1)

    return {
        "total_expense": total,  # USD
        "expense_count": cnt,
        "avg_per_expense": (total / cnt) if cnt else Decimal("0"),
        "avg_per_day": (total / Decimal(days)) if days else Decimal("0"),
    }


def expense_timeseries(store_id: int, start, end, interval: Interval = "day") -> List[Dict[str, Any]]:
    trunc = TRUNC[interval]
    qs = (
        Expense.objects.filter(
            store_id=store_id, is_deleted=False, date__gte=start, date__lt=end
        )
        .annotate(ts=trunc("date"))
        .values("ts")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("ts")
    )
    return list(qs)


def expense_breakdown_by_reason(
        store_id: int, start, end, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    qs = (
        Expense.objects.filter(
            store_id=store_id, is_deleted=False, date__gte=start, date__lt=end
        )
        .values("reason")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    data = list(qs)
    for row in data:
        row["label"] = REASON_LABELS.get(row["reason"], row["reason"])
    return data[:limit] if (limit and limit > 0) else data


def expense_other_top_custom_reasons(
        store_id: int, start, end, limit: int = 10
) -> List[Dict[str, Any]]:
    qs = (
        Expense.objects.filter(
            store_id=store_id,
            is_deleted=False,
            reason="OTHER",
            date__gte=start,
            date__lt=end,
        )
        .values("custom_reason")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:limit]
    )
    return list(qs)
