from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum


class Cashbox(models.Model):
    store = models.OneToOneField("store.Store", on_delete=models.CASCADE, related_name="cashbox")
    balance = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.store.name} kassasi"

    class Meta:
        verbose_name = "Do'kon kassasi"
        verbose_name_plural = "Do'kon kassalari"

    def calculate_balance(self):
        income = self.transactions.filter(is_out=False).aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        expense = self.transactions.filter(is_out=True).aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        return (income - expense).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)

    def refresh_balance(self):
        self.balance = self.calculate_balance()
        self.save(update_fields=['balance'])


class CashTransaction(models.Model):
    cashbox = models.ForeignKey(Cashbox, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=20, decimal_places=6)
    is_out = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0.00"))

    order = models.ForeignKey("order.Order", null=True, blank=True, on_delete=models.CASCADE)
    expense = models.ForeignKey("expense.Expense", null=True, blank=True, on_delete=models.CASCADE, related_name='cash_transactions')
    entry_system = models.ForeignKey("systems.ProductEntrySystem", null=True, blank=True, on_delete=models.CASCADE)
    manual_source = models.CharField(max_length=100, blank=True, help_text="Qo‘lda kiritilgan manba nomi")

    debt_document = models.ForeignKey("loan.DebtDocument", null=True, blank=True, on_delete=models.CASCADE, related_name='cash_debts')

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Kassa qismi"
        verbose_name_plural = "Kassa qismlari"

    def get_full_note(self):
        if self.order:
            return f"Buyurtma: #{self.order.pk}"
        elif self.expense:
            return f"Xarajat: {self.expense.get_full_reason()}"
        elif self.entry_system:
            return f"Mahsulot kirimi: {self.entry_system.product.name} ({self.entry_system.count} dona)"
        elif self.manual_source:
            return f"Qo‘lda kiritilgan: {self.manual_source}"
        elif self.note:
            return f"Izoh: {self.note}"
        elif self.debt_document:
            return f"Qarz hujjati: {self.debt_document.id} ({self.debt_document.debtuser})"
        return "Manba aniqlanmagan"

    def __str__(self):
        direction = "Chiqim" if self.is_out else "Kirim"
        return f"{direction}: {self.amount} ({self.cashbox.store.name})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.cashbox.refresh_balance()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.cashbox.refresh_balance()
