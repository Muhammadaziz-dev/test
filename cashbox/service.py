from cashbox.models import CashTransaction


class CashboxService:
    @staticmethod
    def income(cashbox, amount, rate, note='', **sources):
        return CashTransaction.objects.create(cashbox=cashbox, amount=amount, is_out=False, exchange_rate=rate,
                                              note=note, **sources)

    @staticmethod
    def expense(cashbox, amount, rate, note='', **sources):
        return CashTransaction.objects.create(cashbox=cashbox, amount=amount, is_out=True, exchange_rate=rate,
                                              note=note, **sources)
