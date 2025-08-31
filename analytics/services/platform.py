# analytics/services/platform.py
from decimal import Decimal
from typing import List, Dict, Any, Literal, Optional

from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.db.models import ExpressionWrapper as EW

from order.models import Order, ProductOrder
from systems.models import ProductSale
from expense.models import Expense
from cashbox.models import CashTransaction
from loan.models import DebtUser, DebtDocument
from product.models import Product
from refund.models import Refund

Interval = Literal["day", "week", "month"]
TRUNC = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}

# ---- Helpers ----

def _stores_q(store_ids: List[int]):
    if not store_ids:
        # himoya; bo'sh bo'lsa hech narsa qaytarmaydi
        return Q(pk__in=[])
    return Q(store_id__in=store_ids)


# ---- 1. Overview (asosiy KPI) ----

def platform_overview(store_ids: List[int], start, end) -> Dict[str, Any]:
    # Sales
    sales_qs = (Order.objects.active()
                .filter(_stores_q(store_ids), created_at__gte=start, created_at__lt=end))
    s = sales_qs.aggregate(
        revenue=Sum("total_price"),
        net_profit=Sum("total_profit"),
        orders=Count("id"),
        paid=Sum("paid_amount"),
        change=Sum("change_amount"),
    )
    units = ProductOrder.objects.filter(
        order__created_at__gte=start, order__created_at__lt=end,
        order__is_deleted=False, order__store_id__in=store_ids,
    ).aggregate(units=Sum("quantity"))

    revenue = s["revenue"] or Decimal("0")
    orders_count = s["orders"] or 0

    # Expenses
    e = Expense.objects.filter(store_id__in=store_ids, is_deleted=False, date__gte=start, date__lt=end)\
                        .aggregate(total=Sum("amount"), count=Count("id"))

    # Cash flows (period inflow/outflow)
    c = CashTransaction.objects.filter(cashbox__store_id__in=store_ids, created_at__gte=start, created_at__lt=end)\
                                .aggregate(inflow=Sum("amount", filter=Q(is_out=False)),
                                           outflow=Sum("amount", filter=Q(is_out=True)))

    # Debts (period flow + outstanding)
    # USD normalize: DebtDocument model saqlashi shart, bu yerda faqat total_amount ishlatamiz
    dd = DebtDocument.objects.filter(store_id__in=store_ids, is_deleted=False, date__gte=start, date__lt=end)\
                              .aggregate(
                                  transferred=Sum("total_amount", filter=Q(method="transfer")),
                                  accepted=Sum("total_amount", filter=Q(method="accept")),
                              )
    du = DebtUser.objects.filter(store_id__in=store_ids)\
                         .aggregate(outstanding=Sum(EW(
                             # balance USD ekvivalent
                             F("balance") / F("exchange_rate"), output_field=DecimalField(max_digits=24, decimal_places=6)
                         )),
                                    debtors=Count("id", filter=Q(balance__gt=0)))

    # Inventory (on-hand qiymat va potensial tushum)
    p_qs = Product.objects.filter(store_id__in=store_ids, is_deleted=False)
    on_hand = F("count") + F("warehouse_count")
    inv_value = EW(on_hand * F("enter_price"), output_field=DecimalField(max_digits=30, decimal_places=6))
    pot_rev = EW(on_hand * F("out_price"), output_field=DecimalField(max_digits=30, decimal_places=6))
    inv = p_qs.aggregate(on_hand_qty=Sum(on_hand), inv_value=Sum(inv_value), pot_revenue=Sum(pot_rev))

    # Refunds (period)
    r = Refund.objects.filter(
        Q(product_order__order__store_id__in=store_ids) | Q(document_product__document__store_id__in=store_ids),
        created_at__gte=start, created_at__lt=end
    ).aggregate(count=Count("id"), units=Sum("quantity"))

    return {
        "sales": {
            "revenue": revenue,
            "net_profit": s["net_profit"] or Decimal("0"),
            "orders": orders_count,
            "aov": (revenue / orders_count) if orders_count else Decimal("0"),
            "units_sold": units["units"] or 0,
        },
        "expenses": {
            "total": e["total"] or Decimal("0"),
            "count": e["count"] or 0,
        },
        "cash": {
            "inflow": c["inflow"] or Decimal("0"),
            "outflow": c["outflow"] or Decimal("0"),
            "net_flow": (c["inflow"] or Decimal("0")) - (c["outflow"] or Decimal("0")),
        },
        "debt": {
            "transferred": dd["transferred"] or Decimal("0"),
            "accepted": dd["accepted"] or Decimal("0"),
            "net_flow": (dd["transferred"] or Decimal("0")) - (dd["accepted"] or Decimal("0")),
            "outstanding": du["outstanding"] or Decimal("0"),
            "active_debtors": du["debtors"] or 0,
        },
        "inventory": {
            "on_hand_qty": inv["on_hand_qty"] or 0,
            "inventory_value_usd": inv["inv_value"] or Decimal("0"),
            "potential_revenue_usd": inv["pot_revenue"] or Decimal("0"),
        },
        "refunds": {
            "count": r["count"] or 0,
            "units": r["units"] or 0,
        },
        "ratios": {
            "profit_margin": ((s["net_profit"] or 0) / revenue) if revenue else Decimal("0"),
            "expense_ratio": ((e["total"] or 0) / revenue) if revenue else Decimal("0"),
            "refund_rate": ((r["units"] or 0) / (units["units"] or 1)),
            "debt_repayment_rate": ((dd["accepted"] or 0) / (dd["transferred"] or 1)),
        }
    }


# ---- 2. Timeseries (jamlangan) ----

def platform_timeseries(store_ids: List[int], start, end, interval: Interval = "day") -> List[Dict[str, Any]]:
    trunc = TRUNC[interval]
    # Sales
    s = (Order.objects.active()
         .filter(_stores_q(store_ids), created_at__gte=start, created_at__lt=end)
         .annotate(ts=trunc("created_at"))
         .values("ts")
         .annotate(revenue=Sum("total_price"), profit=Sum("total_profit"), orders=Count("id")))

    # Expenses
    e = (Expense.objects.filter(store_id__in=store_ids, is_deleted=False, date__gte=start, date__lt=end)
         .annotate(ts=trunc("date")).values("ts").annotate(expense=Sum("amount")))

    # Cash
    c = (CashTransaction.objects.filter(cashbox__store_id__in=store_ids, created_at__gte=start, created_at__lt=end)
         .annotate(ts=trunc("created_at")).values("ts").annotate(
            inflow=Sum("amount", filter=Q(is_out=False)),
            outflow=Sum("amount", filter=Q(is_out=True)),
         ))

    # Merge by ts
    by_ts: Dict[Any, Dict[str, Any]] = {}
    for r in s:
        ts = r["ts"]
        by_ts.setdefault(ts, {"revenue": Decimal("0"), "profit": Decimal("0"), "orders": 0, "expense": Decimal("0"), "inflow": Decimal("0"), "outflow": Decimal("0")})
        by_ts[ts]["revenue"] += r["revenue"] or 0
        by_ts[ts]["profit"] += r["profit"] or 0
        by_ts[ts]["orders"] += r["orders"] or 0
    for r in e:
        ts = r["ts"]
        by_ts.setdefault(ts, {"revenue": Decimal("0"), "profit": Decimal("0"), "orders": 0, "expense": Decimal("0"), "inflow": Decimal("0"), "outflow": Decimal("0")})
        by_ts[ts]["expense"] += r["expense"] or 0
    for r in c:
        ts = r["ts"]
        by_ts.setdefault(ts, {"revenue": Decimal("0"), "profit": Decimal("0"), "orders": 0, "expense": Decimal("0"), "inflow": Decimal("0"), "outflow": Decimal("0")})
        by_ts[ts]["inflow"] += r["inflow"] or 0
        by_ts[ts]["outflow"] += r["outflow"] or 0

    out = []
    for ts in sorted(by_ts.keys()):
        d = by_ts[ts]
        out.append({
            "ts": ts,
            "revenue": d["revenue"],
            "profit": d["profit"],
            "orders": d["orders"],
            "expense": d["expense"],
            "cash_net": (d["inflow"] - d["outflow"]) if (d["inflow"] or d["outflow"]) else Decimal("0"),
        })
    return out


# ---- 3. TOP do'konlar ----

def top_stores(store_ids: List[int], start, end, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    # Revenue/profit bo'yicha
    s = (Order.objects.active()
         .filter(_stores_q(store_ids), created_at__gte=start, created_at__lt=end)
         .values("store_id", "store__name")
         .annotate(revenue=Sum("total_price"), profit=Sum("total_profit"), orders=Count("id")))

    # Expense bo'yicha
    e = (Expense.objects.filter(store_id__in=store_ids, is_deleted=False, date__gte=start, date__lt=end)
         .values("store_id").annotate(expense=Sum("amount")))
    e_map = {r["store_id"]: r["expense"] or Decimal("0") for r in e}

    rows = []
    for r in s:
        rid = r["store_id"]
        rows.append({
            "store_id": rid,
            "store_name": r.get("store__name"),
            "revenue": r["revenue"] or Decimal("0"),
            "profit": r["profit"] or Decimal("0"),
            "orders": r["orders"] or 0,
            "expense": e_map.get(rid, Decimal("0")),
            "margin": ( (r["profit"] or 0) / (r["revenue"] or 1) ) if (r["revenue"] or 0) else Decimal("0"),
        })

    top_by_revenue = sorted(rows, key=lambda x: x["revenue"], reverse=True)[:limit]
    top_by_profit  = sorted(rows, key=lambda x: x["profit"],  reverse=True)[:limit]
    best_margin    = sorted(rows, key=lambda x: x["margin"],  reverse=True)[:limit]

    return {"by_revenue": top_by_revenue, "by_profit": top_by_profit, "by_margin": best_margin}


# ---- 4. To'lov turlari bo'yicha taqsimot ----

def payment_split_multi(store_ids: List[int], start, end) -> List[Dict[str, Any]]:
    qs = (Order.objects.active()
          .filter(_stores_q(store_ids), created_at__gte=start, created_at__lt=end)
          .values("payment_type")
          .annotate(amount=Sum("paid_amount"), orders=Count("id"))
          .order_by("-amount"))
    return list(qs)