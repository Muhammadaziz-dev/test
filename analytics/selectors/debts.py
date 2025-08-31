from django.db.models import Sum, Value, F, DecimalField, ExpressionWrapper, Case, When
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def _sum_positive_diff(qs, left_expr, right_expr, out_name='diff_usd'):
    qs = qs.annotate(_diff=ExpressionWrapper(left_expr - right_expr,
                         output_field=DecimalField(max_digits=20, decimal_places=6)))
    qs = qs.annotate(**{
        out_name: Case(
            When(_diff__gt=Value(D0), then=F('_diff')),
            default=Value(D0),
            output_field=DecimalField(max_digits=20, decimal_places=6),
        )
    })
    return qs.aggregate(v=Coalesce(Sum(out_name), Value(D0),
                     output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0

from django.db.models import Sum, Value, F, DecimalField, ExpressionWrapper, Case, When
from django.db.models.functions import Coalesce
from ..utils.model_helpers import get_model, find_field, date_range_kwargs, try_filter_store
from ..utils.money import as_usd, D0


def _sum_usd(qs, field_name, currency='currency', rate='exchange_rate'):
    Model = qs.model
    if find_field(Model, [currency]) and find_field(Model, [rate]):
        qs = qs.annotate(val_usd=as_usd(field_name, currency, rate))
        return qs.aggregate(v=Coalesce(Sum('val_usd'), Value(D0),
                                       output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0
    return qs.aggregate(v=Coalesce(Sum(field_name), Value(D0),
                                   output_field=DecimalField(max_digits=20, decimal_places=6)))['v'] or D0

def compute_debts(date_from, date_to, store_id=None, source='auto'):
    """
    Soddalashtirilgan qoidalar (DebtDocument bo'lsa):
      debt_given_usd  = Σ transfer.total_amount
      debt_taken_usd  = Σ accept.total_amount
      receivables_outstanding_usd = max( Σ transfer.total_amount − Σ accept.total_amount, 0 )
    Supplier qarzlari (Import/Purchase) o'zgarmagan.
    """
    out = {
        'debt_given_usd': D0,
        'debt_taken_usd': D0,
        'receivables_outstanding_usd': D0,
        'payables_outstanding_usd': D0,
        'sources': {
            'given': 'none',
            'taken': 'none',
            'recv_out': 'none',
            'pay_out': 'none',
        },
    }

    DebtDocument = get_model('DebtDocument')
    use_docs = (source == 'docs') or (source == 'auto' and DebtDocument is not None)

    # ---------- A) DebtDocument asosida (soddalashtirilgan) ----------
    if use_docs and DebtDocument:
        # davr ichida
        kwargs_p = date_range_kwargs(DebtDocument, date_from, date_to)
        transfers = try_filter_store(
            DebtDocument.objects.filter(**kwargs_p, is_deleted=False, method='transfer'),
            store_id, ['store_id', 'store__id']
        )
        accepts = try_filter_store(
            DebtDocument.objects.filter(**kwargs_p, is_deleted=False, method='accept'),
            store_id, ['store_id', 'store__id']
        )

        out['debt_given_usd'] = _sum_usd(transfers, 'total_amount')
        out['debt_taken_usd'] = _sum_usd(accepts,   'total_amount')
        out['sources']['given'] = 'DebtDocument.transfer.total_amount (normalized)'
        out['sources']['taken'] = 'DebtDocument.accept.total_amount (normalized)'

        # date_to holatidagi qoldiq
        kwargs_to = date_range_kwargs(DebtDocument, date_from.replace(year=1970, month=1, day=1), date_to)
        transfers_to = try_filter_store(
            DebtDocument.objects.filter(**kwargs_to, is_deleted=False, method='transfer'),
            store_id, ['store_id', 'store__id']
        )
        accepts_to = try_filter_store(
            DebtDocument.objects.filter(**kwargs_to, is_deleted=False, method='accept'),
            store_id, ['store_id', 'store__id']
        )

        t_total_to = _sum_usd(transfers_to, 'total_amount')
        a_total_to = _sum_usd(accepts_to,   'total_amount')
        recv_out = t_total_to - a_total_to
        out['receivables_outstanding_usd'] = recv_out if recv_out > D0 else D0
        out['sources']['recv_out'] = 'Σtransfer.total − Σaccept.total (normalized)'

        # Supplier qarzlari yo'q bo'lsa 0 bo'lib qoladi (pastdagi fallback’ga o‘tmaymiz)
        return out