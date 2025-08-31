from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_opex(date_from, date_to, store_id=None):
    Expense = get_model('Expense')
    if Expense:
        kwargs_e = date_range_kwargs(Expense, date_from, date_to)
        qs_e = try_filter_store(Expense.objects.filter(**kwargs_e), store_id, ['store_id', 'cashbox__store_id', 'store__id'])
        if find_field(Expense, ['currency']) and find_field(Expense, ['exchange_rate']):
            qs_e = qs_e.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
            v = qs_e.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
            return v or D0, 'Expense.amount (normalized)'
        v = qs_e.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
        return v or D0, 'Expense.amount'

    CashTransaction = get_model('CashTransaction')
    if CashTransaction:
        kwargs_c = date_range_kwargs(CashTransaction, date_from, date_to)
        qs_c = try_filter_store(CashTransaction.objects.filter(type='EXPENSE', **kwargs_c), store_id, ['store_id', 'cashbox__store_id', 'store__id'])
        if find_field(CashTransaction, ['currency']) and find_field(CashTransaction, ['exchange_rate']):
            qs_c = qs_c.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
            v = qs_c.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
            return v or D0, 'CashTransaction.EXPENSE (normalized)'
        v = qs_c.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
        return v or D0, 'CashTransaction.EXPENSE'

    return D0, 'none'