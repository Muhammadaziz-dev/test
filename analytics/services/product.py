# analytics/services/product.py
from decimal import Decimal
from typing import Literal, List, Dict, Any, Optional

from django.db.models import Sum, Count, F, Q, DecimalField
from django.db.models import ExpressionWrapper as EW
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

from product.models import Product, StockEntry, WasteEntry
from systems.models import ProductSale

Interval = Literal["day", "week", "month"]
TRUNC = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}

# --- 1. Inventory metrics (zaxira holati) ---

def inventory_metrics(store_id: int) -> Dict[str, Any]:
    qs = Product.objects.filter(store_id=store_id, is_deleted=False)

    on_hand_expr = F("count") + F("warehouse_count")
    inv_value_expr = EW(on_hand_expr * F("enter_price"), output_field=DecimalField(max_digits=30, decimal_places=6))
    potential_rev_expr = EW(on_hand_expr * F("out_price"), output_field=DecimalField(max_digits=30, decimal_places=6))

    agg = qs.aggregate(
        sku_count=Count("id"),
        in_stock=Count("id", filter=Q(count__gt=0) | Q(warehouse_count__gt=0)),
        shelf_qty=Sum("count"),
        warehouse_qty=Sum("warehouse_count"),
        on_hand_qty=Sum(on_hand_expr),
        inventory_value=Sum(inv_value_expr),
        potential_revenue=Sum(potential_rev_expr),
    )

    inventory_value = agg["inventory_value"] or Decimal("0")
    potential_revenue = agg["potential_revenue"] or Decimal("0")
    margin_value = potential_revenue - inventory_value
    margin_rate = (margin_value / potential_revenue) if potential_revenue else Decimal("0")

    return {
        "sku_count": agg["sku_count"] or 0,
        "in_stock_sku": agg["in_stock"] or 0,
        "shelf_qty": agg["shelf_qty"] or 0,
        "warehouse_qty": agg["warehouse_qty"] or 0,
        "on_hand_qty": agg["on_hand_qty"] or 0,
        "inventory_value_usd": inventory_value,
        "potential_revenue_usd": potential_revenue,
        "margin_value_usd": margin_value,
        "margin_rate": margin_rate,
    }

# --- 2. Harakatlar timeseries (inflow/outflow) ---

def movement_timeseries(store_id: int, start, end, interval: Interval = "day", include_debt: bool = True) -> List[Dict[str, Any]]:
    trunc = TRUNC[interval]

    # Inflow: barcha StockEntry (importlar, qaytarishlar, debt accept, refund DISLIKED/OTHER)
    inflow = (
        StockEntry.objects
        .filter(product__store_id=store_id, created_at__gte=start, created_at__lt=end)
        .annotate(ts=trunc("created_at"))
        .values("ts")
        .annotate(
            in_qty=Sum("quantity"),
            in_value=Sum(EW(F("quantity") * F("unit_price"), output_field=DecimalField(max_digits=30, decimal_places=6)))
        )
    )

    # Outflow: sotuvlar (ProductSale)
    sales = (
        ProductSale.objects
        .filter(order__store_id=store_id, created_at__gte=start, created_at__lt=end)
        .annotate(ts=trunc("created_at"))
        .values("ts")
        .annotate(out_qty=Sum("quantity"), out_value=Sum("total_price"))
    )

    # Outflow qo‘shimcha: debt transfer (ixtiyoriy)
    dp_by_ts = {}
    if include_debt:
        from loan.models import DocumentProduct
        from django.db.models import Case, When
        dp = (
            DocumentProduct.objects
            .filter(
                product__store_id=store_id,
                document__date__gte=start,
                document__date__lt=end,
                document__method="transfer",
                document__is_deleted=False,
            )
            .annotate(ts=trunc("document__date"))
            .values("ts")
            .annotate(
                out_qty=Sum("quantity"),
                out_value=Sum(EW(
                    Case(
                        When(currency="UZS", then=F("amount") / F("exchange_rate")),
                        default=F("amount"),
                        output_field=DecimalField(max_digits=30, decimal_places=6)
                    ),
                    output_field=DecimalField(max_digits=30, decimal_places=6)
                )),
            )
        )
        for r in dp:
            dp_by_ts[r["ts"]] = {"out_qty": r["out_qty"] or 0, "out_value": r["out_value"] or Decimal("0")}

    # Merge
    by_ts: Dict[Any, Dict[str, Any]] = {}

    for r in inflow:
        ts = r["ts"]
        by_ts.setdefault(ts, {"in_qty": 0, "in_value": Decimal("0"), "out_qty": 0, "out_value": Decimal("0")})
        by_ts[ts]["in_qty"] = r["in_qty"] or 0
        by_ts[ts]["in_value"] = r["in_value"] or Decimal("0")

    for r in sales:
        ts = r["ts"]
        by_ts.setdefault(ts, {"in_qty": 0, "in_value": Decimal("0"), "out_qty": 0, "out_value": Decimal("0")})
        by_ts[ts]["out_qty"] += r["out_qty"] or 0
        by_ts[ts]["out_value"] += r["out_value"] or Decimal("0")

    for ts, add in dp_by_ts.items():
        by_ts.setdefault(ts, {"in_qty": 0, "in_value": Decimal("0"), "out_qty": 0, "out_value": Decimal("0")})
        by_ts[ts]["out_qty"] += add["out_qty"]
        by_ts[ts]["out_value"] += add["out_value"]

    data = []
    for ts in sorted(by_ts.keys()):
        d = by_ts[ts]
        net_qty = (d["in_qty"] or 0) - (d["out_qty"] or 0)
        net_value = (d["in_value"] or Decimal("0")) - (d["out_value"] or Decimal("0"))
        data.append({
            "ts": ts,
            "in_qty": d["in_qty"],
            "out_qty": d["out_qty"],
            "in_value_usd": d["in_value"],
            "out_value_usd": d["out_value"],
            "net_qty": net_qty,
            "net_value_usd": net_value,
        })
    return data

# --- 3. TOP lar: revenue/profit/units/waste ---

def top_products(store_id: int, start, end, limit: int = 10, include_debt: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    # Sotuvlar bo‘yicha TOP (revenue/profit/units)
    s = (
        ProductSale.objects
        .filter(order__store_id=store_id, created_at__gte=start, created_at__lt=end)
        .values("product_id", "product__name")
        .annotate(revenue=Sum("total_price"), profit=Sum("profit"), units=Sum("quantity"))
    )
    by_pid = { (r["product_id"], r["product__name"]): r for r in s }

    # Debt transfer’lardan units/out_value qo‘shish (ixtiyoriy)
    if include_debt:
        from loan.models import DocumentProduct
        from django.db.models import Case, When
        dp = (
            DocumentProduct.objects
            .filter(
                product__store_id=store_id,
                document__date__gte=start,
                document__date__lt=end,
                document__method="transfer",
                document__is_deleted=False,
            )
            .values("product_id", "product__name")
            .annotate(
                dp_units=Sum("quantity"),
                dp_value=Sum(EW(
                    Case(
                        When(currency="UZS", then=F("amount") / F("exchange_rate")),
                        default=F("amount"),
                        output_field=DecimalField(max_digits=30, decimal_places=6)
                    ),
                    output_field=DecimalField(max_digits=30, decimal_places=6)
                )),
            )
        )
        for r in dp:
            key = (r["product_id"], r["product__name"])
            base = by_pid.setdefault(key, {"product_id": r["product_id"], "product__name": r["product__name"], "revenue": Decimal("0"), "profit": Decimal("0"), "units": 0, "dp_value": Decimal("0")})
            base["units"] = (base.get("units") or 0) + (r["dp_units"] or 0)
            base["dp_value"] = (base.get("dp_value") or Decimal("0")) + (r["dp_value"] or Decimal("0"))

    all_rows = list(by_pid.values())

    top_by_revenue = sorted(all_rows, key=lambda x: (x.get("revenue") or Decimal("0")), reverse=True)[:limit]
    top_by_profit  = sorted(all_rows, key=lambda x: (x.get("profit") or Decimal("0")),  reverse=True)[:limit]
    top_by_units   = sorted(all_rows, key=lambda x: (x.get("units")  or 0),                 reverse=True)[:limit]

    # Waste bo‘yicha TOP
    waste = (
        WasteEntry.objects
        .filter(product__store_id=store_id, created_at__gte=start, created_at__lt=end)
        .values("product_id", "product__name", "reason")
        .annotate(qty=Sum("quantity"))
    )
    # qiymat USD (tannarx) bo‘yicha
    from django.db.models import FloatField
    waste_by_pid = {}
    for r in waste:
        key = (r["product_id"], r["product__name"])
        waste_by_pid.setdefault(key, {"product_id": r["product_id"], "product__name": r["product__name"], "qty": 0})
        waste_by_pid[key]["qty"] += r["qty"] or 0
    top_by_waste = sorted(waste_by_pid.values(), key=lambda x: x["qty"], reverse=True)[:limit]

    return {
        "by_revenue": top_by_revenue,
        "by_profit": top_by_profit,
        "by_units": top_by_units,
        "by_waste_qty": top_by_waste,
    }

# --- 4. Waste breakdown (sabablar bo‘yicha) ---

def waste_breakdown(store_id: int, start, end) -> List[Dict[str, Any]]:
    qs = (
        WasteEntry.objects
        .filter(product__store_id=store_id, created_at__gte=start, created_at__lt=end)
        .values("reason")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")
    )
    return list(qs)

# --- 5. Slow movers (sotilmayotgan qoldiq) ---

def slow_movers(store_id: int, as_of, min_days: int = 30, top_n: int = 20, include_debt: bool = True) -> List[Dict[str, Any]]:
    from django.db.models import Max
    prods = Product.objects.filter(store_id=store_id, is_deleted=False).annotate(on_hand=F("count") + F("warehouse_count"))

    # So‘nggi sotuv sanasi (ProductSale)
    last_sale = (
        ProductSale.objects
        .filter(order__store_id=store_id)
        .values("product_id")
        .annotate(last=Max("created_at"))
    )
    last_sale_map = {r["product_id"]: r["last"] for r in last_sale}

    # Debt transfer ham faoliyat sifatida hisoblang (ixtiyoriy)
    last_transfer_map = {}
    if include_debt:
        from loan.models import DocumentProduct
        last_transfer = (
            DocumentProduct.objects
            .filter(product__store_id=store_id, document__method="transfer", document__is_deleted=False)
            .values("product_id")
            .annotate(last=Max("document__date"))
        )
        last_transfer_map = {r["product_id"]: r["last"] for r in last_transfer}

    items = []
    for p in prods:
        if (p.on_hand or 0) <= 0:
            continue
        l1 = last_sale_map.get(p.id)
        l2 = last_transfer_map.get(p.id)
        last = l1 if (l1 and (not l2 or l1 >= l2)) else l2
        days = (as_of - last).days if last else 99999
        if days >= min_days:
            items.append({
                "product_id": p.id,
                "name": p.name,
                "on_hand": p.on_hand,
                "days_since_activity": days,
                "last_activity": last,
            })
    items.sort(key=lambda x: (x["days_since_activity"], -x["on_hand"]), reverse=True)
    return items[:top_n]

# --- 6. Low cover (qoplash kunlari kam) ---

def low_cover(store_id: int, start, end, cover_days: int = 7, min_avg_daily: float = 0.1, top_n: int = 20, include_debt: bool = True) -> List[Dict[str, Any]]:
    days = max((end - start).days, 1)
    # Sotuv + debt transfer birliklari bo‘yicha o‘rtacha kunlik chiqim
    sales = (
        ProductSale.objects
        .filter(order__store_id=store_id, created_at__gte=start, created_at__lt=end)
        .values("product_id")
        .annotate(units=Sum("quantity"))
    )
    usage_map = {r["product_id"]: (r["units"] or 0) for r in sales}

    if include_debt:
        from loan.models import DocumentProduct
        dp = (
            DocumentProduct.objects
            .filter(product__store_id=store_id, document__date__gte=start, document__date__lt=end, document__method="transfer", document__is_deleted=False)
            .values("product_id")
            .annotate(units=Sum("quantity"))
        )
        for r in dp:
            usage_map[r["product_id"]] = usage_map.get(r["product_id"], 0) + (r["units"] or 0)

    prods = Product.objects.filter(store_id=store_id, is_deleted=False).annotate(on_hand=F("count") + F("warehouse_count"))

    res = []
    for p in prods:
        on_hand = p.on_hand or 0
        avg_daily = (usage_map.get(p.id, 0) / days)
        avg_daily = max(avg_daily, min_avg_daily)  # nolga bo‘linmaslik va juda kichik bo‘lsa ham meaningful bo‘lishi uchun
        cover = on_hand / avg_daily
        if cover <= cover_days:
            res.append({
                "product_id": p.id,
                "name": p.name,
                "on_hand": on_hand,
                "avg_daily_out": round(avg_daily, 3),
                "days_of_cover": round(cover, 2),
            })

    res.sort(key=lambda x: x["days_of_cover"])  # eng xavfli birinchi
    return res[:top_n]

# --- 7. Recent stock entries ---

def recent_stock_entries(store_id: int, start, end, limit: int = 20) -> List[Dict[str, Any]]:
    qs = (
        StockEntry.objects
        .filter(product__store_id=store_id, created_at__gte=start, created_at__lt=end)
        .select_related("product", "debt")
        .order_by("-created_at")[:limit]
    )
    items = []
    for e in qs:
        source = "debt" if getattr(e, "debt_id", None) else ("warehouse" if e.is_warehouse else "shelf")
        items.append({
            "id": e.id,
            "created_at": e.created_at,
            "product_id": e.product_id,
            "product_name": e.product.name if e.product else None,
            "quantity": e.quantity,
            "unit_price_usd": e.unit_price,
            "total_value_usd": (e.unit_price or Decimal("0")) * (e.quantity or 0),
            "is_warehouse": e.is_warehouse,
            "source": source,
        })
    return items