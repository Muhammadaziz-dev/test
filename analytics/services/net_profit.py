# analytics/services/net_profit.py
from decimal import Decimal
from ..selectors.turnover import compute_turnover
from ..selectors.gross_profit import compute_gross_profit
from ..selectors.expenses import compute_opex
from ..selectors.salaries import compute_salaries
from ..selectors.outflows import compute_total_outflows
from ..selectors.debts import compute_debts
from ..selectors.debt_profit import compute_debt_profit
from ..selectors.imports import compute_imports   # ⬅️ YANGI

D0 = Decimal('0')

def compute(
    date_from,
    date_to,
    store_id=None,
    *,
    turnover_mode='sales',
    outflow_mode='ops+salary',
    out_types=None,
    debts_source='auto',
    imports_mode='pure',          # ⬅️ YANGI
):
    turnover, t_src = compute_turnover(date_from, date_to, store_id, mode=turnover_mode)
    gross, g_src = compute_gross_profit(date_from, date_to, store_id)
    opex, e_src = compute_opex(date_from, date_to, store_id)
    salaries, s_src = compute_salaries(date_from, date_to, store_id)
    total_out, out_src = compute_total_outflows(
        date_from, date_to, store_id, opex, salaries, mode=outflow_mode, extra_types=out_types
    )
    net = (gross or D0) - (opex or D0) - (salaries or D0)

    debts = compute_debts(date_from, date_to, store_id, source=debts_source)
    dprofit = compute_debt_profit(date_from, date_to, store_id, debts_source=debts_source)

    imports_totals, imp_src = compute_imports(date_from, date_to, store_id, mode=imports_mode)  # ⬅️ YANGI

    return {
        'turnover_usd': turnover,
        'gross_profit_usd': gross,
        'operating_expenses_usd': opex,
        'salaries_usd': salaries,
        'total_outflows_usd': total_out,
        'net_profit_usd': net,

        # Debts
        'debt_given_usd': debts.get('debt_given_usd', D0),
        'debt_taken_usd': debts.get('debt_taken_usd', D0),
        'receivables_outstanding_usd': debts.get('receivables_outstanding_usd', D0),
        'payables_outstanding_usd': debts.get('payables_outstanding_usd', D0),

        # Debt profit
        'debt_profit_usd': dprofit['debt_profit_usd'],
        'receivables_profit_usd': dprofit['receivables_profit_usd'],

        # ⬅️ YANGI: Imports
        'imports_quantity': imports_totals['quantity'],
        'imports_value_usd': imports_totals['value_usd'],

        'sources': {
            'turnover': t_src,
            'sales': g_src,
            'expenses': e_src,
            'salaries': s_src,
            'outflows': out_src,
            'debts': debts['sources'],
            'debt_profit': dprofit['sources'],
            'imports': f"{imp_src} [mode={imports_mode}]",   # ⬅️ YANGI
        }
    }
