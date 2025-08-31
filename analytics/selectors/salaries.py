from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def compute_salaries(date_from, date_to, store_id=None):
    SalaryPayment = get_model('SalaryPayment')
    if not SalaryPayment:
        return D0, 'none'
    kwargs_s = date_range_kwargs(SalaryPayment, date_from, date_to)
    qs_s = try_filter_store(SalaryPayment.objects.filter(**kwargs_s), store_id, ['store_id', 'employee__store_id', 'store__id'])
    if find_field(SalaryPayment, ['currency']) and find_field(SalaryPayment, ['exchange_rate']):
        qs_s = qs_s.annotate(amount_usd=as_usd('amount', 'currency', 'exchange_rate'))
        v = qs_s.aggregate(v=Coalesce(Sum('amount_usd'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
        return v or D0, 'SalaryPayment.amount (normalized)'
    v = qs_s.aggregate(v=Coalesce(Sum('amount'), Value(D0), output_field=DecimalField(max_digits=20, decimal_places=6)))['v']
    return v or D0, 'SalaryPayment.amount'