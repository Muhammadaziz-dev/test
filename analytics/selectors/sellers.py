# analytics/selectors/sellers.py
from decimal import Decimal
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db.models import (
    Sum, Count, Value, F, DecimalField, ExpressionWrapper, Case, When, IntegerField
)
from django.db.models.functions import Coalesce

from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def _normalize_seller_field(Order, candidate: str | None):
    """
    Qaytaradi: (group_field, base_path, rel_model)
      - group_field: values()/filter() uchun full path (mas: 'owner' yoki 'cashtransaction__user__user')
      - base_path:   label uchun (group_field dan *_id olib tashlangan)
      - rel_model:   to'g'ridan-to'g'ri FK bo'lsa (chuqur path bo'lsa None)
    """
    if candidate:
        name = candidate.strip()
        base = name[:-3] if name.endswith('_id') else name
        rel_model = None
        if '__' not in base:
            try:
                field = Order._meta.get_field(base)
                rel_model = field.remote_field.model if field.remote_field else None
            except FieldDoesNotExist:
                rel_model = None
        return name, base, rel_model

    # Order ga owner qo'shilgani uchun shu birinchi navbatda sinaymiz
    direct_candidates = [
        'owner', 'seller', 'user', 'cashier', 'staff',
        'created_by', 'createdby', 'creator', 'author',
        'owner_id', 'seller_id', 'user_id', 'cashier_id', 'staff_id', 'created_by_id'
    ]
    name = find_field(Order, direct_candidates)
    if name:
        base = name[:-3] if name.endswith('_id') else name
        rel_model = None
        try:
            field = Order._meta.get_field(base)
            rel_model = field.remote_field.model if field.remote_field else None
        except FieldDoesNotExist:
            rel_model = None
        return name, base, rel_model

    return None, None, None


def _products_sold_per_seller(date_from, date_to, store_id, seller_base_path: str):
    """
    ProductSale bo'yicha Σ(quantity) ni sotuvchi kesimida qaytaradi.
    seller_base_path: Order dagi sotuvchi pathi ('owner' yoki 'cashtransaction__user__user' va h.k.)
    """
    ProductSale = get_model('ProductSale')
    if not ProductSale or not seller_base_path:
        return {}, 'none'

    qty_field = find_field(ProductSale, ['quantity', 'qty', 'count'])
    order_fk = find_field(ProductSale, ['order'])
    if not (qty_field and order_fk):
        return {}, 'ProductSale missing quantity/order fields'

    kwargs_ps = date_range_kwargs(ProductSale, date_from, date_to)
    ps = ProductSale.objects.filter(**kwargs_ps)
    ps = try_filter_store(ps, store_id, ['order__store_id', 'store_id', 'order__store__id'])

    seller_path = f'{order_fk}__{seller_base_path}'
    try:
        grouped = ps.values(seller_path).annotate(
            seller_id=F(seller_path),
            products_sold=Coalesce(Sum(qty_field, output_field=IntegerField()), Value(0)),
        )
    except FieldError:
        return {}, f'ProductSale path not found: {seller_path}'

    out = {row['seller_id']: int(row['products_sold'] or 0) for row in grouped}
    return out, f'ProductSale.{qty_field} grouped by Order.{seller_base_path}'


def _auto_fallback_grouping(qs, initial_group_field: str | None):
    """
    values(...).annotate(...) qilganda FieldError bo'lsa — chuqur yo'llar bo'yicha avto qidiramiz.
    """
    candidates = []
    if initial_group_field:
        candidates.append(initial_group_field)

    # Avvalo Order.owner, keyin boshqa ehtimoliy yo'llar
    candidates += [
        'owner', 'owner__user',
        'cashtransaction__user__user',        'cashtransaction__user',
        'cashtransaction__owner__user',       'cashtransaction__owner',
        'cashtransaction__created_by__user',  'cashtransaction__created_by',
        'sales__user__user',                  'sales__user',
        'sales__owner__user',                 'sales__owner',
        'sales__created_by__user',            'sales__created_by',
        'user__user', 'user', 'created_by__user', 'created_by',
    ]

    for gf in candidates:
        try:
            list(qs.values(gf).annotate(test_count=Count('id'))[:1])
            return gf
        except FieldError:
            continue
    return None


def _build_label_map(group_field: str, seller_ids):
    """
    group_field ga qarab, seller_id -> readable label (ism) mapini Python tarafda tayyorlaydi.
    - Agar group_field CustomUser ga ishora qilsa (…__user), CustomUser’dan ism oladi.
    - Agar PlatformUser bo‘lsa (owner), PlatformUser.user’dan ism oladi.
    """
    label_map = {}
    if not seller_ids:
        return label_map

    CustomUser = get_model('CustomUser')   # accounts.CustomUser
    PlatformUser = get_model('PlatformUser')  # platform_user.PlatformUser

    ids = list({sid for sid in seller_ids if sid is not None})

    try:
        if group_field.endswith('__user') or group_field.endswith('__user_id') or group_field in ('user', 'user_id'):
            if CustomUser:
                rows = CustomUser.objects.filter(pk__in=ids).values('id', 'first_name', 'last_name', 'username', 'phone_number')
                for r in rows:
                    full = f"{(r['first_name'] or '').strip()} {(r['last_name'] or '').strip()}".strip()
                    label_map[r['id']] = full or r['username'] or r['phone_number'] or str(r['id'])
        elif 'owner' in group_field:
            if PlatformUser:
                rows = PlatformUser.objects.select_related('user').filter(pk__in=ids)\
                    .values('id', 'user__first_name', 'user__last_name', 'user__username', 'user__phone_number')
                for r in rows:
                    full = f"{(r['user__first_name'] or '').strip()} {(r['user__last_name'] or '').strip()}".strip()
                    label_map[r['id']] = full or r['user__username'] or r['user__phone_number'] or str(r['id'])
        # boshqa hollarda label bo'sh qoladi
    except Exception:
        pass

    return label_map


def compute_seller_summary(
    date_from,
    date_to,
    store_id=None,
    *,
    order_by='profit',     # 'profit' | 'revenue' | 'orders' | 'avg_check' | 'commission' | 'products'
    limit: int | None = 10,
    commission_rate: Decimal | float | None = None,
    seller_field: str | None = None,
):
    Order = get_model('Order')
    if not Order:
        return {'sellers': [], 'seller_field': None, 'source': 'none'}

    kwargs_o = date_range_kwargs(Order, date_from, date_to)
    qs = Order.objects.filter(**kwargs_o)
    qs = try_filter_store(qs, store_id, ['store_id', 'store__id'])

    for flag in ['is_deleted', 'deleted', 'is_canceled', 'is_cancelled']:
        if find_field(Order, [flag]):
            qs = qs.filter(**{flag: False})
            break

    group_field, seller_base, rel_model = _normalize_seller_field(Order, seller_field)

    # FX normalize
    has_fx = find_field(Order, ['currency']) and find_field(Order, ['exchange_rate'])
    price_field = find_field(Order, ['total_price', 'amount', 'sum']) or 'total_price'
    profit_field = find_field(Order, ['total_profit', 'profit']) or 'total_profit'
    paid_field = find_field(Order, ['paid_amount', 'paid', 'payment', 'paid_sum'])

    price_usd = as_usd(price_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(price_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    profit_usd = as_usd(profit_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(profit_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    paid_usd = (
        as_usd(paid_field, 'currency', 'exchange_rate')
        if (has_fx and paid_field)
        else (ExpressionWrapper(F(paid_field), output_field=DecimalField(max_digits=20, decimal_places=6))
              if paid_field else Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))
    )

    qs = qs.annotate(
        _price_usd=price_usd,
        _profit_usd=profit_usd,
        _paid_usd=paid_usd,
    ).annotate(
        _diff=ExpressionWrapper(F('_price_usd') - F('_paid_usd'),
                                output_field=DecimalField(max_digits=20, decimal_places=6)),
        unpaid_usd=Case(
            When(_diff__gt=Value(D0), then=F('_diff')),
            default=Value(D0),
            output_field=DecimalField(max_digits=20, decimal_places=6),
        )
    )

    # Avto group_field
    group_field = _auto_fallback_grouping(qs, group_field)
    if not group_field:
        return {'sellers': [], 'seller_field': None, 'source': 'Order by date (no seller path found)'}

    # seller bo'sh bo'lgan buyurtmalarni olib tashlaymiz
    try:
        qs = qs.filter(**{f"{group_field}__isnull": False})
    except FieldError:
        pass

    # distinct buyer (xaridorlar soni)
    customer_field = find_field(Order, ['debtuser', 'customer', 'client', 'user_customer', 'buyer', 'customer_id'])
    phone_field = find_field(Order, ['phone_number', 'phone', 'msisdn'])
    distinct_expr = F(customer_field) if customer_field else (F(phone_field) if phone_field else F('id'))

    grouped = qs.values(group_field).annotate(
        seller_id=F(group_field),
        orders_count=Count('id'),
        customers_count=Count(distinct_expr, distinct=True),
        revenue_usd=Coalesce(Sum('_price_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        profit_usd=Coalesce(Sum('_profit_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        unpaid_sum_usd=Coalesce(Sum('unpaid_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
    )
    rows = list(grouped)

    # Label mapni Python tarafda yig'amiz
    label_map = _build_label_map(group_field, [r['seller_id'] for r in rows])
    for r in rows:
        r['seller_label'] = label_map.get(r['seller_id'], '')

    # ProductSale'dan Σ(quantity)
    seller_base = group_field[:-3] if group_field.endswith('_id') else group_field
    products_map, prod_src = _products_sold_per_seller(date_from, date_to, store_id, seller_base)
    for r in rows:
        r['products_sold'] = int(products_map.get(r['seller_id'], 0))

    # Post-calc
    rate = Decimal(str(commission_rate)) if commission_rate is not None else None
    for r in rows:
        orders = r['orders_count'] or 0
        rev = r['revenue_usd'] or D0
        prof = r['profit_usd'] or D0
        r['avg_check_usd'] = (rev / orders) if orders else D0
        r['commission_usd'] = (prof * rate) if rate is not None else None

    # Sorting
    key_map = {
        'profit':     lambda x: x['profit_usd'],
        'revenue':    lambda x: x['revenue_usd'],
        'orders':     lambda x: x['orders_count'],
        'avg_check':  lambda x: x['avg_check_usd'],
        'commission': lambda x: (x['commission_usd'] or D0),
        'products':   lambda x: x['products_sold'],
    }
    key_fn = key_map.get(order_by, key_map['profit'])
    rows.sort(key=key_fn, reverse=True)
    if limit and limit > 0:
        rows = rows[:limit]

    return {
        'sellers': rows,
        'seller_field': group_field,
        'source': f"Order grouped by {group_field} (normalized totals); products via {prod_src}"
    }


def compute_seller_detail(date_from, date_to, store_id, seller_id, *, seller_field: str | None = None):
    Order = get_model('Order')
    if not Order:
        return {
            'seller_id': seller_id, 'orders_count': 0, 'revenue_usd': D0, 'profit_usd': D0,
            'unpaid_sum_usd': D0, 'products_sold': 0, 'source': 'none'
        }

    kwargs_o = date_range_kwargs(Order, date_from, date_to)
    qs = Order.objects.filter(**kwargs_o)
    qs = try_filter_store(qs, store_id, ['store_id', 'store__id'])

    for flag in ['is_deleted', 'deleted', 'is_canceled', 'is_cancelled']:
        if find_field(Order, [flag]):
            qs = qs.filter(**{flag: False})
            break

    group_field, seller_base, _ = _normalize_seller_field(Order, seller_field)
    group_field = _auto_fallback_grouping(qs, group_field)
    if not group_field:
        return {
            'seller_id': seller_id, 'orders_count': 0, 'revenue_usd': D0, 'profit_usd': D0,
            'unpaid_sum_usd': D0, 'products_sold': 0, 'source': 'Order (no seller path found)'
        }

    try:
        qs = qs.filter(**{group_field: seller_id})
    except FieldError:
        return {
            'seller_id': seller_id, 'orders_count': 0, 'revenue_usd': D0, 'profit_usd': D0,
            'unpaid_sum_usd': D0, 'products_sold': 0, 'source': f'Invalid seller path: {group_field}'
        }

    has_fx = find_field(Order, ['currency']) and find_field(Order, ['exchange_rate'])
    price_field = find_field(Order, ['total_price', 'amount', 'sum']) or 'total_price'
    profit_field = find_field(Order, ['total_profit', 'profit']) or 'total_profit'
    paid_field = find_field(Order, ['paid_amount', 'paid', 'payment', 'paid_sum'])

    price_usd = as_usd(price_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(price_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    profit_usd = as_usd(profit_field, 'currency', 'exchange_rate') if has_fx else \
        ExpressionWrapper(F(profit_field), output_field=DecimalField(max_digits=20, decimal_places=6))
    paid_usd = (
        as_usd(paid_field, 'currency', 'exchange_rate')
        if (has_fx and paid_field)
        else (ExpressionWrapper(F(paid_field), output_field=DecimalField(max_digits=20, decimal_places=6))
              if paid_field else Value(D0, output_field=DecimalField(max_digits=20, decimal_places=6)))
    )

    qs = qs.annotate(
        _price_usd=price_usd,
        _profit_usd=profit_usd,
        _paid_usd=paid_usd,
    ).annotate(
        _diff=ExpressionWrapper(F('_price_usd') - F('_paid_usd'),
                                output_field=DecimalField(max_digits=20, decimal_places=6)),
        unpaid_usd=Case(
            When(_diff__gt=Value(D0), then=F('_diff')),
            default=Value(D0),
            output_field=DecimalField(max_digits=20, decimal_places=6),
        )
    )

    agg = qs.aggregate(
        orders_count=Coalesce(Count('id'), Value(0)),
        revenue_usd=Coalesce(Sum('_price_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        profit_usd=Coalesce(Sum('_profit_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
        unpaid_sum_usd=Coalesce(Sum('unpaid_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)),
    )

    # products_sold
    seller_base = group_field[:-3] if group_field.endswith('_id') else group_field
    products_map, prod_src = _products_sold_per_seller(date_from, date_to, store_id, seller_base)
    products_sold = int(products_map.get(seller_id, 0))

    # label
    label_map = _build_label_map(group_field, [seller_id])

    agg['seller_id'] = seller_id
    agg['seller_label'] = label_map.get(seller_id, '')
    agg['products_sold'] = products_sold
    agg['source'] = f"Order filtered by {group_field}={seller_id}; products via {prod_src}"
    return agg
