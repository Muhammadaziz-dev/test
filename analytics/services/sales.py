from decimal import Decimal
from typing import Literal
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from order.models import Order, ProductOrder
from systems.models import ProductSale
from django.utils import timezone

Interval = Literal["day", "week", "month"]

TRUNC = {
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
}


def sales_metrics(store_id: int, start, end):
    qs = (Order.objects.active()
          .filter(store_id=store_id, created_at__gte=start, created_at__lt=end))

    totals = qs.aggregate(
        revenue=Sum("total_price"),
        net_profit=Sum("total_profit"),
        orders=Count("id"),
        paid=Sum("paid_amount"),
        change=Sum("change_amount"),
    )

    units = ProductOrder.objects.filter(
        order__store_id=store_id,
        order__created_at__gte=start,
        order__created_at__lt=end,
        order__is_deleted=False,
    ).aggregate(units=Sum("quantity"))

    revenue = totals["revenue"] or Decimal("0")
    orders_count = totals["orders"] or 0

    return {
        "revenue": revenue,
        "net_profit": totals["net_profit"] or Decimal("0"),
        "orders": orders_count,
        "aov": (revenue / orders_count) if orders_count else Decimal("0"),
        "units_sold": units["units"] or 0,
        "paid_amount": totals["paid"] or Decimal("0"),
        "change_amount": totals["change"] or Decimal("0"),
    }


def sales_timeseries(store_id: int, start, end, interval: Interval = "day"):
    trunc = TRUNC[interval]
    qs = (Order.objects.active()
          .filter(store_id=store_id, created_at__gte=start, created_at__lt=end)
          .annotate(ts=trunc("created_at"))
          .values("ts")
          .annotate(revenue=Sum("total_price"), profit=Sum("total_profit"), orders=Count("id"))
          .order_by("ts"))
    return list(qs)


def top_products(store_id: int, start, end, by: Literal["revenue", "profit"] = "revenue", limit: int = 10):
    agg_field = "total_price" if by == "revenue" else "profit"
    qs = (ProductSale.objects
    .filter(order__store_id=store_id, created_at__gte=start, created_at__lt=end)
    .values("product_id", "product__name")
    .annotate(metric=Sum(agg_field), quantity=Sum("quantity"))
    .order_by("-metric")[:limit])
    return list(qs)


def payment_split(store_id: int, start, end):
    qs = (Order.objects.active()
          .filter(store_id=store_id, created_at__gte=start, created_at__lt=end)
          .values("payment_type")
          .annotate(amount=Sum("paid_amount"), orders=Count("id"))
          .order_by("-amount"))
    return list(qs)
