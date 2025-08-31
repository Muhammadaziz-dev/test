# analytics/services/refund.py
from decimal import Decimal
from typing import Literal, List, Dict, Any, Optional

from django.db.models import Sum, Count, Case, When, Value, Q, F, DecimalField, CharField, IntegerField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, Coalesce
from django.db.models import ExpressionWrapper as EW

from refund.models import Refund

Interval = Literal["day", "week", "month"]
TRUNC = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}

SOURCE_CASE = Case(
    When(product_order__isnull=False, then=Value("order")),
    When(document_product__isnull=False, then=Value("debt")),
    default=Value("unknown"),
    output_field=CharField(),
)


RESTOCK_REASON = ["DISLIKED", "OTHER"]


def _base_qs(store_id: int, start, end):
    return (
        Refund.objects
        .filter(created_at__gte=start, created_at__lt=end)
        .filter(
            Q(product_order__order__store_id=store_id) |
            Q(document_product__document__store_id=store_id)
        )
    )


def refund_metrics(store_id: int, start, end) -> Dict[str, Any]:
    qs = _base_qs(store_id, start, end)

    agg = qs.aggregate(
        refunds=Count("id"),
        units=Sum("quantity"),
        restock_units=Sum("quantity", filter=Q(reason_type__in=RESTOCK_REASON)),
        waste_units=Sum("quantity", filter=Q(reason_type="UNUSABLE")),
        order_refunds=Count("id", filter=Q(product_order__isnull=False)),
        debt_refunds=Count("id", filter=Q(document_product__isnull=False)),
    )

    # restock/waste qiymati: enter_price (USD) * quantity
    unit_cost = Case(
        When(product_order__isnull=False, then=F("product_order__product__enter_price")),
        When(document_product__isnull=False, then=F("document_product__product__enter_price")),
        default=Value(Decimal('0')),
        output_field=DecimalField(max_digits=30, decimal_places=6)
    )
    restock_value = qs.filter(reason_type__in=RESTOCK_REASON).aggregate(
        v=Sum(EW(unit_cost * F("quantity"), output_field=DecimalField(max_digits=30, decimal_places=6)))
    )["v"] or Decimal("0")
    waste_cost = qs.filter(reason_type="UNUSABLE").aggregate(
        v=Sum(EW(unit_cost * F("quantity"), output_field=DecimalField(max_digits=30, decimal_places=6)))
    )["v"] or Decimal("0")

    # revenue reversal (faqat order tarafidagi refund’lar): Python darajasida to‘plash
    revenue_reversed = Decimal("0")
    for r in qs.select_related("product_order"):
        if r.product_order:
            try:
                price_usd = r.product_order.get_price_usd()
                revenue_reversed += (price_usd * r.quantity)
            except Exception:
                pass

    return {
        "refunds": agg["refunds"] or 0,
        "units": agg["units"] or 0,
        "order_refunds": agg["order_refunds"] or 0,
        "debt_refunds": agg["debt_refunds"] or 0,
        "restock_units": agg["restock_units"] or 0,
        "waste_units": agg["waste_units"] or 0,
        "restock_value_usd": restock_value,
        "waste_cost_usd": waste_cost,
        "revenue_reversed_usd": revenue_reversed,
    }


def refund_timeseries(store_id: int, start, end, interval: Interval = "day") -> List[Dict[str, Any]]:
    trunc = TRUNC[interval]
    qs = _base_qs(store_id, start, end).annotate(ts=trunc("created_at"))

    base = (
        qs.values("ts")
        .annotate(
            refunds=Count("id"),
            units=Sum("quantity"),
            restock_units=Sum("quantity", filter=Q(reason_type__in=RESTOCK_REASON)),
            waste_units=Sum("quantity", filter=Q(reason_type="UNUSABLE")),
        )
        .order_by("ts")
    )

    # qiymatlarni tashlandiq/tannarx bo‘yicha
    unit_cost = Case(
        When(product_order__isnull=False, then=F("product_order__product__enter_price")),
        When(document_product__isnull=False, then=F("document_product__product__enter_price")),
        default=Value(Decimal('0')),
        output_field=DecimalField(max_digits=30, decimal_places=6)
    )

    val = (
        qs
        .values("ts")
        .annotate(
            restock_value=Sum(EW(unit_cost * F("quantity"), output_field=DecimalField(max_digits=30, decimal_places=6)),
                              filter=Q(reason_type__in=RESTOCK_REASON)),
            waste_cost=Sum(EW(unit_cost * F("quantity"), output_field=DecimalField(max_digits=30, decimal_places=6)),
                           filter=Q(reason_type="UNUSABLE"))
        )
    )
    val_map = {
        r["ts"]: {"restock_value": r["restock_value"] or Decimal("0"), "waste_cost": r["waste_cost"] or Decimal("0")}
        for r in val}

    out = []
    for r in base:
        ts = r["ts"]
        m = val_map.get(ts, {"restock_value": Decimal("0"), "waste_cost": Decimal("0")})
        out.append({
            "ts": ts,
            "refunds": r["refunds"],
            "units": r["units"] or 0,
            "restock_units": r["restock_units"] or 0,
            "waste_units": r["waste_units"] or 0,
            "restock_value_usd": m["restock_value"],
            "waste_cost_usd": m["waste_cost"],
        })
    return out


def refund_breakdown_by_reason(store_id: int, start, end) -> List[Dict[str, Any]]:
    qs = _base_qs(store_id, start, end)
    return list(
        qs.values("reason_type")
        .annotate(count=Count("id"), units=Sum("quantity"))
        .order_by("-units")
    )


def refund_breakdown_by_source(store_id: int, start, end) -> List[Dict[str, Any]]:
    qs = _base_qs(store_id, start, end).annotate(source=SOURCE_CASE)
    return list(
        qs.values("source")
        .annotate(count=Count("id"), units=Sum("quantity"))
        .order_by("-units")
    )


def top_refunded_products(store_id: int, start, end, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Eng ko'p qaytarilgan mahsulotlar (units bo'yicha).
    Case/When bilan product_id va product_name ni annotatsiya qilib,
    to'g'ridan-to'g'ri shu aliaslar bilan groupby qilamiz — 'key' o'zgaruvchisiga ehtiyoj yo'q.
    """
    qs = _base_qs(store_id, start, end)

    product_name = Case(
        When(product_order__isnull=False, then=F("product_order__product__name")),
        When(document_product__isnull=False, then=F("document_product__product__name")),
        default=Value("Unknown"),
        output_field=CharField(),
    )
    product_id = Case(
        When(product_order__isnull=False, then=F("product_order__product_id")),
        When(document_product__isnull=False, then=F("document_product__product_id")),
        default=Value(None),
        output_field=IntegerField(),
    )

    rows = (
        qs.annotate(product_id=product_id, product_name=product_name)
          .values("product_id", "product_name")
          .annotate(units=Sum("quantity"))
          .order_by("-units")[:limit]
    )
    return list(rows)


def other_top_custom_reasons(store_id: int, start, end, limit: int = 10) -> List[Dict[str, Any]]:
    qs = _base_qs(store_id, start, end).filter(reason_type="OTHER")
    return list(
        qs.values("custom_reason")
        .annotate(count=Count("id"), units=Sum("quantity"))
        .order_by("-units")[:limit]
    )


def recent_refunds(store_id: int, start, end, limit: int = 20) -> List[Dict[str, Any]]:
    qs = (
        _base_qs(store_id, start, end)
        .select_related("product_order__product", "document_product__product")
        .order_by("-created_at")[:limit]
    )

    items = []
    for r in qs:
        if r.product_order:
            src = "order"
            pname = r.product_order.product.name if r.product_order.product else None
        else:
            src = "debt"
            pname = r.document_product.product.name if r.document_product and r.document_product.product else None
        items.append({
            "id": r.id,
            "created_at": r.created_at,
            "source": src,
            "reason_type": r.reason_type,
            "custom_reason": r.custom_reason,
            "quantity": r.quantity,
            "product_name": pname,
        })
    return items
