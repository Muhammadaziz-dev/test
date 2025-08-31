from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_total_outflows(date_from, date_to, store_id, opex, salaries, mode='ops+salary', extra_types=None):
    total = (opex or D0) + (salaries or D0)
    source_parts = ['operating_expenses', 'salaries']

    if mode == 'all':
        CashTransaction = get_model('CashTransaction')
        if CashTransaction:
            kwargs_co = date_range_kwargs(CashTransaction, date_from, date_to)
            qs_co = try_filter_store(CashTransaction.objects.filter(**kwargs_co), store_id, ['store_id', 'cashbox__store_id', 'store__id'])
            tfield = find_field(CashTransaction, ['type'])
            if tfield:
                default_types = ['PURCHASE', 'SUPPLIER_PAYMENT', 'TAX', 'LOAN_REPAYMENT', 'WITHDRAWAL', 'OTHER_OUT']
                types = [t.strip().upper() for t in (extra_types or default_types)]
                qs_co = qs_co.filter(**{f"{tfield}__in": types})
            if find_field(CashTransaction, ['currency']) and find_field(CashTransaction, ['exchange_rate']):
                qs_co = qs_co.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
                extra = qs_co.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            else:
                extra = qs_co.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
            total += extra
            source_parts.append('CashTransaction[extra_outflows]')

    return total, '+'.join(source_parts)