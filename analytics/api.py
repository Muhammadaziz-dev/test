from typing import List, Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_datetime, parse_date
from django.utils import timezone
from datetime import timedelta, datetime, time

from .services.sales import sales_metrics, sales_timeseries, top_products, payment_split

from analytics.services.debt import (
    debt_metrics,
    debt_timeseries,
    top_debtors,
    debt_ageing,
    debt_breakdown,
    recent_debt_documents,
)

from analytics.services.expense import (
    expense_metrics,
    expense_timeseries,
    expense_breakdown_by_reason,
    expense_other_top_custom_reasons,
)

from analytics.services.cash import (
    cash_metrics,
    cash_timeseries,
    cash_breakdown_by_source,
    recent_transactions,
    largest_transactions,
)

from analytics.services.product import (
    inventory_metrics,
    movement_timeseries,
    top_products,
    waste_breakdown,
    slow_movers,
    low_cover,
    recent_stock_entries,
)

from analytics.services.refund import (
    refund_metrics,
    refund_timeseries,
    refund_breakdown_by_reason,
    refund_breakdown_by_source,
    top_refunded_products,
    other_top_custom_reasons,
    recent_refunds,
)

from analytics.services.platform import (
    platform_overview,
    platform_timeseries,
    top_stores,
    payment_split_multi,
)



ALLOWED_INTERVALS = {"day", "week", "month"}


def _parse_dt(s, fallback_start=False):
    """
    '2025-08-01' yoki '2025-08-01T13:45:00Z' formatlarini qabul qiladi.
    Naive bo‘lsa, current TZ bilan aware qiladi.
    """
    if not s:
        return None
    dt = parse_datetime(s)
    if not dt:
        d = parse_date(s)
        if d:
            dt = datetime.combine(d, time.min if fallback_start else time.max)
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def resolve_accessible_store_id(user) -> list[int]:
    """
    TODO: Loyiha tuzilmasiga moslab to'ldiring.
    Masalan, PlatformUser orqali: PlatformUser(user=user).stores.values_list('id', flat=True)
    Hozircha bo'sh ro'yxat qaytarilsa, API store_id'ni majburiy qiladi.
    """
    return []


class SalesAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        store_id = kwargs.get("store_id") or request.query_params.get("store_id")
        if store_id is None:
            return Response({"detail": "store_id majburiy (path yoki query orqali)."}, status=400)
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return Response({"detail": "store_id butun son bo‘lishi kerak."}, status=400)

        interval = request.query_params.get("interval", "day").lower()
        if interval not in ALLOWED_INTERVALS:
            return Response({"detail": f"interval {ALLOWED_INTERVALS} dan biri bo‘lishi kerak."}, status=400)

        end = _parse_dt(request.query_params.get("end")) or timezone.now()
        start = _parse_dt(request.query_params.get("start"), fallback_start=True) or (end - timedelta(days=30))
        if start >= end:
            return Response({"detail": "start < end bo‘lishi kerak."}, status=400)

        data = {
            "metrics": sales_metrics(store_id, start, end),
            "timeseries": sales_timeseries(store_id, start, end, interval),
            "top_products_by_revenue": top_products(store_id, start, end, by="revenue", limit=10),
            "top_products_by_profit": top_products(store_id, start, end, by="profit", limit=10),
            "payment_split": payment_split(store_id, start, end),
            "start": start,
            "end": end,
            "interval": interval,
        }
        return Response(data)


class ExpenseAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        store_id = kwargs.get("store_id") or request.query_params.get("store_id")
        if store_id is None:
            return Response({"detail": "store_id majburiy (path yoki query)."}, status=400)
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return Response({"detail": "store_id butun son bo‘lishi kerak."}, status=400)

        interval = request.query_params.get("interval", "day").lower()
        if interval not in ALLOWED_INTERVALS:
            return Response({"detail": f"interval {ALLOWED_INTERVALS} dan biri."}, status=400)

        end = _parse_dt(request.query_params.get("end")) or timezone.now()
        start = _parse_dt(request.query_params.get("start"), fallback_start=True) or (end - timedelta(days=30))
        if start >= end:
            return Response({"detail": "start < end bo‘lishi kerak."}, status=400)

        top_n = request.query_params.get("top_n")
        try:
            top_n = int(top_n) if top_n is not None else None
        except ValueError:
            return Response({"detail": "top_n butun son bo‘lishi kerak."}, status=400)

        data = {
            "metrics": expense_metrics(store_id, start, end),
            "timeseries": expense_timeseries(store_id, start, end, interval),
            "by_reason": expense_breakdown_by_reason(store_id, start, end, limit=top_n),
            "other_top_custom": expense_other_top_custom_reasons(store_id, start, end, limit=10),
            "start": start,
            "end": end,
            "interval": interval,
        }
        return Response(data)


class CashAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        store_id = kwargs.get("store_id") or request.query_params.get("store_id")
        if store_id is None:
            return Response({"detail": "store_id majburiy (path yoki query)."}, status=400)
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return Response({"detail": "store_id butun son bo‘lishi kerak."}, status=400)

        interval = request.query_params.get("interval", "day").lower()
        if interval not in ALLOWED_INTERVALS:
            return Response({"detail": f"interval {ALLOWED_INTERVALS} dan biri."}, status=400)

        end = _parse_dt(request.query_params.get("end")) or timezone.now()
        start = _parse_dt(request.query_params.get("start"), fallback_start=True) or (end - timedelta(days=30))
        if start >= end:
            return Response({"detail": "start < end bo‘lishi kerak."}, status=400)

        top_n = request.query_params.get("top_n")
        try:
            top_n = int(top_n) if top_n is not None else None
        except ValueError:
            return Response({"detail": "top_n butun son."}, status=400)

        data = {
            "metrics": cash_metrics(store_id, start, end),
            "timeseries": cash_timeseries(store_id, start, end, interval),
            "by_source": cash_breakdown_by_source(store_id, start, end, limit=top_n),
            "recent": recent_transactions(store_id, start, end, limit=20),
            "largest": largest_transactions(store_id, start, end, limit=10),
            "start": start,
            "end": end,
            "interval": interval,
        }
        return Response(data)


class DebtAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        store_id = kwargs.get("store_id") or request.query_params.get("store_id")
        if store_id is None:
            return Response({"detail": "store_id majburiy (path yoki query)."}, status=400)
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return Response({"detail": "store_id butun son bo‘lishi kerak."}, status=400)

        interval = request.query_params.get("interval", "day").lower()
        if interval not in ALLOWED_INTERVALS:
            return Response({"detail": f"interval {ALLOWED_INTERVALS} dan biri."}, status=400)

        end = _parse_dt(request.query_params.get("end")) or timezone.now()
        start = _parse_dt(request.query_params.get("start"), fallback_start=True) or (end - timedelta(days=30))
        if start >= end:
            return Response({"detail": "start < end bo‘lishi kerak."}, status=400)

        include_mirror = request.query_params.get("include_mirror", "false").lower() in ("1", "true", "yes")

        top_n = request.query_params.get("top_n")
        try:
            top_n = int(top_n) if top_n is not None else 10
        except ValueError:
            return Response({"detail": "top_n butun son."}, status=400)

        buckets = request.query_params.get("buckets")
        if buckets:
            try:
                buckets = [int(x) for x in buckets.split(',') if x.strip()]
            except ValueError:
                return Response({"detail": "buckets vergul bilan ajratilgan sonlar bo‘lishi kerak."}, status=400)
        else:
            buckets = None

        data = {
            "metrics": debt_metrics(store_id, start, end, include_mirror),
            "timeseries": debt_timeseries(store_id, start, end, interval, include_mirror),
            "top_debtors": top_debtors(store_id, limit=top_n),
            "ageing": debt_ageing(store_id, as_of=end, buckets=buckets),
            "breakdown": debt_breakdown(store_id, start, end, include_mirror),
            "recent": recent_debt_documents(store_id, start, end, limit=20, include_mirror=include_mirror),
            "start": start,
            "end": end,
            "interval": interval,
            "include_mirror": include_mirror,
        }
        return Response(data)


class ProductAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        store_id = kwargs.get("store_id") or request.query_params.get("store_id")
        if store_id is None:
            return Response({"detail": "store_id majburiy (path yoki query)."}, status=400)
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return Response({"detail": "store_id butun son bo‘lishi kerak."}, status=400)

        interval = request.query_params.get("interval", "day").lower()
        if interval not in ALLOWED_INTERVALS:
            return Response({"detail": f"interval {ALLOWED_INTERVALS} dan biri."}, status=400)

        end = _parse_dt(request.query_params.get("end")) or timezone.now()
        start = _parse_dt(request.query_params.get("start"), fallback_start=True) or (end - timedelta(days=30))
        if start >= end:
            return Response({"detail": "start < end bo‘lishi kerak."}, status=400)

        top_n = request.query_params.get("top_n")
        try:
            top_n = int(top_n) if top_n is not None else 10
        except ValueError:
            return Response({"detail": "top_n butun son."}, status=400)

        include_debt = request.query_params.get("include_debt", "true").lower() in ("1", "true", "yes")

        min_days = int(request.query_params.get("slow_min_days", 30))
        cover_days = int(request.query_params.get("cover_days", 7))

        data = {
            "inventory": inventory_metrics(store_id),
            "movements": movement_timeseries(store_id, start, end, interval, include_debt),
            "tops": top_products(store_id, start, end, limit=top_n, include_debt=include_debt),
            "waste_by_reason": waste_breakdown(store_id, start, end),
            "slow_movers": slow_movers(store_id, as_of=end, min_days=min_days, top_n=top_n, include_debt=include_debt),
            "low_cover": low_cover(store_id, start, end, cover_days=cover_days, top_n=top_n, include_debt=include_debt),
            "recent_entries": recent_stock_entries(store_id, start, end, limit=20),
            "start": start,
            "end": end,
            "interval": interval,
            "include_debt": include_debt,
        }
        return Response(data)



class RefundAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        store_id = kwargs.get("store_id") or request.query_params.get("store_id")
        if store_id is None:
            return Response({"detail": "store_id majburiy (path yoki query)."}, status=400)
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return Response({"detail": "store_id butun son bo‘lishi kerak."}, status=400)

        interval = request.query_params.get("interval", "day").lower()
        if interval not in ALLOWED_INTERVALS:
            return Response({"detail": f"interval {ALLOWED_INTERVALS} dan biri."}, status=400)

        end = _parse_dt(request.query_params.get("end")) or timezone.now()
        start = _parse_dt(request.query_params.get("start"), fallback_start=True) or (end - timedelta(days=30))
        if start >= end:
            return Response({"detail": "start < end bo‘lishi kerak."}, status=400)

        top_n_param = request.query_params.get("top_n")
        try:
            top_n = int(top_n_param) if top_n_param is not None else 10
        except ValueError:
            return Response({"detail": "top_n butun son."}, status=400)

        data = {
            "metrics": refund_metrics(store_id, start, end),
            "timeseries": refund_timeseries(store_id, start, end, interval),
            "by_reason": refund_breakdown_by_reason(store_id, start, end),
            "by_source": refund_breakdown_by_source(store_id, start, end),
            "top_products": top_refunded_products(store_id, start, end, limit=top_n),
            "other_top_custom": other_top_custom_reasons(store_id, start, end, limit=top_n),
            "recent": recent_refunds(store_id, start, end, limit=20),
            "start": start,
            "end": end,
            "interval": interval,
        }
        return Response(data)


class PlatformAnalyticsView(APIView):
    """
    Path-based store konteksti:
      GET /platform/<store_id>/analytics/overview/?start=...&end=...&interval=day&top_n=10&store_ids=1,2,3

    - Agar query'da store_ids berilsa => multi-store jamlash (store_ids ishlatiladi)
    - Aks holda => faqat path'dagi bitta store_id bo'yicha jamlanadi
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 1) Majburiy: pathdagi store_id
        store_id = kwargs.get("store_id")
        if store_id is None:
            return Response({"detail": "store_id majburiy (path)."}, status=400)
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return Response({"detail": "store_id butun son bo'lishi kerak."}, status=400)

        # 2) Ixtiyoriy: store_ids (CSV/bitta id/int). Bardoshli parsing.
        raw = request.query_params.get("store_ids", None)
        if raw in (None, ""):
            store_ids: List[int] = [store_id]
        else:
            try:
                if isinstance(raw, (list, tuple)):
                    raw = raw[0]
                s = str(raw)
                if "," in s:
                    store_ids = [int(x) for x in s.split(",") if x.strip()]
                else:
                    store_ids = [int(s)]
            except (TypeError, ValueError):
                return Response(
                    {"detail": "store_ids vergul bilan ajratilgan butun son(lar) bo'lishi kerak."},
                    status=400,
                )

        interval = (request.query_params.get("interval") or "day").lower()
        if interval not in ALLOWED_INTERVALS:
            return Response({"detail": f"interval {ALLOWED_INTERVALS} dan biri."}, status=400)

        end = _parse_dt(request.query_params.get("end")) or timezone.now()
        start = _parse_dt(request.query_params.get("start"), fallback_start=True) or (end - timedelta(days=30))
        if start >= end:
            return Response({"detail": "start < end bo'lishi kerak."}, status=400)

        top_n_param = request.query_params.get("top_n")
        try:
            top_n = int(top_n_param) if top_n_param is not None else 10
        except ValueError:
            return Response({"detail": "top_n butun son."}, status=400)

        data = {
            "overview": platform_overview(store_ids, start, end),
            "timeseries": platform_timeseries(store_ids, start, end, interval),
            "top_stores": top_stores(store_ids, start, end, limit=top_n),
            "payment_split": payment_split_multi(store_ids, start, end),
            "store_ids": store_ids,
            "start": start,
            "end": end,
            "interval": interval,
        }
        return Response(data)

