from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from cashbox.models import CashTransaction
from cashbox.service import CashboxService
from platform_user.exchange import get_default_exchange_rate
from platform_user.models import PlatformUser
from store.models import Store

EXPENSE_REASONS = [
    ("FOOD", "Ovqatlanish"),
    ("RENT", "Ijaralar"),
    ("TAX", "Soliq / kommunal"),
    ("DELIVERY", "Yetkazib berish"),
    ("TRANSPORT", "Transport (yo‘l, benzin, avtobus)"),
    ("SALARY", "Ish haqi"),
    ("BONUS", "Bonuslar / mukofotlar"),
    ("INTERNET", "Internet / telefon to‘lovi"),
    ("MARKETING", "Reklama / marketing"),
    ("EQUIPMENT", "Jihozlar xaridi / ta'miri"),
    ("SUPPLY", "Kancelyariya / boshqa ofis tovarlari"),
    ("CLEANING", "Tozalik va gigiyena"),
    ("MAINTENANCE", "Texnik xizmat (suv, elektr, ta'mir)"),
    ("SOFTWARE", "Dasturiy ta'minot (platforma, lisenziya)"),
    ("SECURITY", "Xavfsizlik (kamera, signalizatsiya)"),
    ("LOAN", "Kredit / qarz to‘lovi"),
    ("TAX_PENALTY", "Jarimalar / kechiktirilgan soliqlar"),
    ("INSURANCE", "Sug‘urta"),
    ("TRAINING", "Trening / kurslar"),
    ("GIFTS", "Mijozlarga sovg‘alar / aktsiyalar"),
    ("OTHER", "Boshqa"),
]

def validate_custom_reason(value):
    if value and len(value.strip()) < 5:
        raise ValidationError("Boshqa sabab kamida 5 ta belgidan iborat bo'lishi kerak")


class Expense(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="expenses")
    user  = models.ForeignKey(PlatformUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")
    reason = models.CharField(max_length=20, choices=EXPENSE_REASONS, default="OTHER")
    custom_reason = models.CharField(max_length=255, blank=True, validators=[validate_custom_reason])

    amount = models.DecimalField(max_digits=20, decimal_places=6)
    currency = models.CharField(max_length=10, default='USD', choices=[("UZS", "UZS"), ("USD", "USD")])
    exchange_rate = models.DecimalField(               # foydalanuvchi tahrirlay olmaydi
        max_digits=20, decimal_places=10, default=Decimal("1.0"), editable=False
    )

    note = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    cash_transaction = models.OneToOneField(
        CashTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="linked_expense"
    )

    class Meta:
        verbose_name = "Do'kon xarajati"
        verbose_name_plural = "Do'kon xarajatlari"
        ordering = ['-date']

    # ---------- VALIDATION ----------
    def clean(self):
        errors = {}
        if self.reason == "OTHER" and not (self.custom_reason and self.custom_reason.strip()):
            errors['custom_reason'] = "Sabab 'Boshqa' bo'lsa, qo'shimcha izoh talab qilinadi."
        if self.amount is None or self.amount <= Decimal('0'):
            errors['amount'] = "Xarajat miqdori 0 dan katta bo'lishi kerak."

        # UZS bo'lsa, kurs manbai mavjud bo'lishi shart (save() da qo'yamiz)
        if self.currency == "UZS" and not self._get_owner_rate_safely():
            errors['exchange_rate'] = "Kurs topilmadi: User yoki Store owner uchun USD kursini kiriting."

        if errors:
            raise ValidationError(errors)

        # Decimal format safety
        if isinstance(self.amount, Decimal):
            if self.amount.is_nan() or self.amount.is_infinite():
                raise ValidationError({'amount': "Noto'g'ri miqdor formati"})

    # ---------- UTIL ----------
    def _get_owner_rate_safely(self):
        """Ustuvorlik: expense.user → store.owner → current authenticated user"""
        try:
            if self.user and getattr(self.user, "usd_rate", None):
                return self.user.usd_rate.rate
        except Exception:
            pass
        try:
            owner = getattr(self.store, "owner", None)
            if owner and getattr(owner, "usd_rate", None):
                return owner.usd_rate.rate
        except Exception:
            pass
        try:
            from django_currentuser.middleware import get_current_authenticated_user
            u = get_current_authenticated_user()
            if u:
                return get_default_exchange_rate(u)
        except Exception:
            pass
        return None

    def get_full_reason(self):
        if self.reason == "OTHER":
            return f"Boshqa: {self.custom_reason}"
        return dict(EXPENSE_REASONS).get(self.reason, self.reason)

    def _amount_usd(self) -> Decimal:
        # save() dan so'ng model doimo USD'da saqlanadi; baribir fallback bilan
        amt = self.amount or Decimal("0")
        return amt.quantize(Decimal("0.000001"), ROUND_HALF_UP)

    def _delete_cash_tx_safely(self):
        if self.cash_transaction:
            try:
                self.cash_transaction.delete()  # -> Cashbox.refresh_balance()
            finally:
                self.cash_transaction = None

    def _write_cash_tx(self):
        if self.is_deleted or not hasattr(self.store, "cashbox"):
            self._delete_cash_tx_safely()
            return
        amount_usd = self._amount_usd()
        if amount_usd <= 0:
            self._delete_cash_tx_safely()
            return

        if self.cash_transaction:
            tx = self.cash_transaction
            tx.amount = amount_usd
            tx.is_out = True
            tx.note = self.get_full_reason()
            tx.save(update_fields=['amount', 'is_out', 'note'])
        else:
            tx = CashboxService.expense(
                cashbox=self.store.cashbox,
                amount=amount_usd,
                note=self.get_full_reason(),
                rate=self.exchange_rate,
                expense=self
            )
            self.cash_transaction = tx
            super().save(update_fields=["cash_transaction"])

    def save(self, *args, **kwargs):
        if not self.user:
            try:
                from django_currentuser.middleware import get_current_authenticated_user
                cu = get_current_authenticated_user()
                if cu and hasattr(cu, "platform_profile"):
                    self.user = cu.platform_profile
            except Exception:
                pass

        owner_rate = self._get_owner_rate_safely()
        if self.currency == "UZS" and not owner_rate:
            raise ValidationError({'exchange_rate': "Kurs topilmadi: User yoki Store owner uchun USD kursini kiriting."})
        self.exchange_rate = owner_rate or Decimal("1.0")

        self.full_clean()

        if self.currency == "UZS":
            try:
                self.amount = (self.amount / self.exchange_rate).quantize(Decimal("0.000001"), ROUND_HALF_UP)
                self.currency = "USD"
            except (ZeroDivisionError, InvalidOperation) as e:
                raise ValidationError({'amount': f"Valyuta konvertatsiyasida xato: {str(e)}"}) from e

        with transaction.atomic():
            super().save(*args, **kwargs)
            self._write_cash_tx()

    def soft_delete(self):
        if self.is_deleted:
            return
        with transaction.atomic():
            self.is_deleted = True
            self.deleted_at = timezone.now()
            super().save(update_fields=['is_deleted', 'deleted_at'])
            self._delete_cash_tx_safely()

    def restore(self):
        if not self.is_deleted:
            return
        with transaction.atomic():
            self.is_deleted = False
            self.deleted_at = None
            super().save(update_fields=['is_deleted', 'deleted_at'])
            self._write_cash_tx()

    def delete(self, *args, **kwargs):
        self._delete_cash_tx_safely()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} | {self.store.name} | {self.get_full_reason()} | ${self.amount}"
