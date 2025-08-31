# analytics/views.py
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# SELECTOR & SERVICE lar
from .selectors.turnover import compute_turnover
from .selectors.gross_profit import compute_gross_profit
from .selectors.imports import compute_imports
from .selectors.debts import compute_debts
from .selectors.debt_profit import compute_debt_profit
from .services.net_profit import compute as compute_store_net
from .selectors.product_inventory import compute_product_inventory_stats
from .selectors.sellers import compute_seller_summary, compute_seller_detail
from .selectors.product_tops import compute_products_top_list, compute_product_headliners
from .selectors.orders import compute_orders_summary
from .selectors.product_sales import compute_product_sales
from .selectors.orders_series import compute_orders_series



D0 = Decimal('0')


# --------- helpers: period/date parser ----------
def parse_range(q):
    """
    Query: date_from, date_to (ISO) yoki period ∈ {daily, weekly, monthly, yearly, all}
    """
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
    period = (q.get('period') or '').lower().strip()

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
        df, dt = datetime(1970, 1, 1, 0, 0, 0), now
    else:
        df, dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now

    if timezone.is_naive(df): df = timezone.make_aware(df, tz)
    if timezone.is_naive(dt): dt = timezone.make_aware(dt, tz)
    return df, dt


# ===================== ORDERS =====================
class OrderAnalyticsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request, store_id=None):
        date_from, date_to = parse_range(request.query_params)

        # Yangi: to‘liq orders summary
        o = compute_orders_summary(date_from, date_to, store_id)

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},

            # siz so‘raganlar:
            'orders_count': o['orders_count'],       # Umumiy buyurtmalar soni
            'revenue_usd': o['revenue_usd'],         # Buyurtmalarning umumiy aylanmasi (Σ total_price)
            'profit_usd': o['profit_usd'],           # Umumiy buyurtmalar daromadi (Σ total_profit)
            'inflow_usd': o['inflow_usd'],           # Barcha tushumlar (Σ (paid - change))
            'unpaid_sum_usd': o['unpaid_sum_usd'],   # To‘lanmagan qismi (qarzdorlik)
            'avg_check_usd': o['avg_check_usd'],     # O‘rtacha chek

            'source': o['source'],
        })

    @action(detail=False, methods=['get'], url_path='products')
    def products(self, request, store_id=None):
        """
        Mahsulotlar sotuvi (period ichida):
          - nechta (quantity)
          - qanaqa (product_name/id)
          - qanchaga (avg_unit_price_usd)
          - qanday aylanmada (revenue_usd)
          - qancha foyda bilan (profit_usd)
        Query:
          - by=quantity|revenue|profit  (default=quantity)
          - limit=N (default=50)
        """
        date_from, date_to = parse_range(request.query_params)
        by = (request.query_params.get('by') or 'quantity').lower()
        limit = request.query_params.get('limit')
        limit = int(limit) if (limit and str(limit).isdigit()) else 50

        data = compute_product_sales(date_from, date_to, store_id, order_by=by, limit=limit)

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'by': by,
            'limit': limit,
            'products': data['products'],  # [{product_id, product_name, quantity, revenue_usd, profit_usd, avg_unit_price_usd}]
            'source': data['source'],
        })


    @action(detail=False, methods=['get'], url_path='series')
    def series(self, request, store_id=None):
        """
        Grafikli analitika uchun orders time-series:
          - metrics: orders_count, revenue_usd, profit_usd, inflow_usd, unpaid_sum_usd
        Query:
          - period= daily|weekly|monthly|yearly|all  (yoki date_from/date_to)
          - granularity= day|week|month|year|auto    (default=auto)
          - fill_gaps=true|false                      (default=true)
        """
        date_from, date_to = parse_range(request.query_params)
        gran = (request.query_params.get('granularity') or 'auto').lower()
        fill = (request.query_params.get('fill_gaps') or 'true').lower() != 'false'

        data = compute_orders_series(date_from, date_to, store_id, granularity=gran, fill_gaps=fill)

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'granularity': data['granularity'],
            'series': data['series'],
            'source': data['source'],
        })


# ===================== PRODUCTS (IMPORTS) =====================
class ProductAnalyticsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='imports')
    def imports(self, request, store_id=None):
        date_from, date_to = parse_range(request.query_params)
        imports_mode = (request.query_params.get('imports') or 'pure').lower()  # 'pure' | 'all'
        totals, src = compute_imports(date_from, date_to, store_id, mode=imports_mode)

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'imports_mode': imports_mode,
            'imports_quantity': totals['quantity'],
            'imports_value_usd': totals['value_usd'],
            'sources': {'imports': f'{src} [mode={imports_mode}]'},
        })



    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request, store_id=None):
        """
        Mahsulotlar bo'yicha umumiy statistikalar + headliners:
          - Mahsulotlar soni (obyektlar)
          - Mahsulotlarning umumiy soni (countlari bilan)
          - Ombordagi mahsulot turlarining soni
          - Ombordagi mahsulotlar umumiy soni
          - Eng ko'p daromad keltirgan mahsulot
          - Eng ko'p sotilgan mahsulot
        """
        stats, src = compute_product_inventory_stats(store_id)

        date_from, date_to = parse_range(request.query_params)
        heads = compute_product_headliners(date_from, date_to, store_id)

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'products_total_objects': stats['products_total_objects'],
            'products_total_qty': stats['products_total_qty'],
            'warehouse_product_types': stats['warehouse_product_types'],
            'warehouse_total_qty': stats['warehouse_total_qty'],
            'top_profit_product': heads['top_profit_product'],   # {product_id, product_name, quantity, profit_usd}
            'top_sold_product': heads['top_sold_product'],       # {product_id, product_name, quantity, profit_usd}
            'sources': {
                'products': src,
                'top_profit': heads['sources']['top_profit'],
                'top_quantity': heads['sources']['top_quantity'],
            },
        })

    @action(detail=False, methods=['get'], url_path='top')
    def top(self, request, store_id=None):
        """
        Top N mahsulotlar ro'yxati.
        Query:
          - by=profit|quantity (default=profit)
          - limit=int (default=10)
        """
        by = (request.query_params.get('by') or 'profit').lower()
        limit = request.query_params.get('limit')
        limit = int(limit) if (limit and str(limit).isdigit()) else 10

        date_from, date_to = parse_range(request.query_params)
        data = compute_products_top_list(date_from, date_to, store_id, by=by, limit=limit)

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'by': by,
            'limit': limit,
            'products': data['rows'],
            'source': data['source'],
        })



# ===================== DEBTS =====================
class DebtAnalyticsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request, store_id=None):
        date_from, date_to = parse_range(request.query_params)
        debts_source = (request.query_params.get('debts') or 'auto').lower()  # 'auto' | 'docs' | 'orders'

        debts = compute_debts(date_from, date_to, store_id, source=debts_source)
        dprofit = compute_debt_profit(date_from, date_to, store_id, debts_source=debts_source)

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'debts_source': debts_source,
            'debt_given_usd': debts.get('debt_given_usd', D0),
            'debt_taken_usd': debts.get('debt_taken_usd', D0),
            'receivables_outstanding_usd': debts.get('receivables_outstanding_usd', D0),
            'payables_outstanding_usd': debts.get('payables_outstanding_usd', D0),
            'debt_profit_usd': dprofit['debt_profit_usd'],
            'receivables_profit_usd': dprofit['receivables_profit_usd'],
            'sources': {
                'debts': debts['sources'],
                'debt_profit': dprofit['sources'],
            },
        })


# ===================== STORE (NET PROFIT) =====================
class StoreAnalyticsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='profit')
    def profit(self, request, store_id=None):
        date_from, date_to = parse_range(request.query_params)

        turnover_mode = (request.query_params.get('turnover') or 'sales').lower()     # 'sales' | 'all'
        outflow_mode  = (request.query_params.get('outflow')  or 'ops+salary').lower()# 'ops' | 'ops+salary' | 'all'
        out_types_param = request.query_params.get('out_types')
        out_types = [t.strip().upper() for t in out_types_param.split(',')] if out_types_param else None

        debts_source = (request.query_params.get('debts') or 'auto').lower()          # 'auto' | 'docs' | 'orders'
        imports_mode = (request.query_params.get('imports') or 'pure').lower()        # 'pure' | 'all'

        result = compute_store_net(
            date_from, date_to, store_id,
            turnover_mode=turnover_mode,
            outflow_mode=outflow_mode,
            out_types=out_types,
            debts_source=debts_source,
            imports_mode=imports_mode,
        )

        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'turnover_mode': turnover_mode,
            'outflow_mode': outflow_mode,
            'debts_source': debts_source,
            'imports_mode': imports_mode,
            **result,
        })


from .selectors.sellers import compute_seller_summary, compute_seller_detail

class SellerAnalyticsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request, store_id=None):
        date_from, date_to = parse_range(request.query_params)
        order_by = (request.query_params.get('by') or 'profit').lower()
        limit = request.query_params.get('limit')
        limit = int(limit) if (limit and str(limit).isdigit()) else 10
        commission = request.query_params.get('commission')
        commission_rate = float(commission) if commission is not None else None

        seller_field = request.query_params.get('seller_field')  # dunder path ham bo'ladi: cashtransaction__user

        data = compute_seller_summary(
            date_from, date_to, store_id,
            order_by=order_by, limit=limit,
            commission_rate=commission_rate,
            seller_field=seller_field,
        )
        return Response({
            'store_id': store_id,
            'period': {'from': date_from, 'to': date_to},
            'order_by': order_by,
            'limit': limit,
            'commission_rate': commission_rate,
            **data,
        })

    @action(detail=True, methods=['get'], url_path='summary')
    def summary_detail(self, request, pk=None, store_id=None):
        date_from, date_to = parse_range(request.query_params)
        seller_field = request.query_params.get('seller_field')
        data = compute_seller_detail(date_from, date_to, store_id, seller_id=pk, seller_field=seller_field)
        return Response({'store_id': store_id, 'period': {'from': date_from, 'to': date_to}, **data})
