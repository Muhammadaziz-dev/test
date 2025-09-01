from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from product.models import Product, StockEntry
from systems.models import StockTransfer
from cashbox.models import CashTransaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.conf import settings
from store.models import Store


class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        # default: soft delete
        self.soft_delete()

    def soft_delete(self):
        if not self.is_deleted:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    def restore(self):
        if self.is_deleted:
            self.is_deleted = False
            self.deleted_at = None
            self.save(update_fields=['is_deleted', 'deleted_at'])

User = get_user_model()

CURRENCY = [
    ('USD', 'USD'),
    ('UZS', 'UZS'),
]

DOCUMENT_METHOD = [
    ('transfer', 'Transfer'),
    ('accept', 'Accept'),
]


class DebtUser(SoftDeleteMixin, models.Model):  # <-- SoftDeleteMixin qo‘shildi
    store = models.ForeignKey('store.Store', on_delete=models.CASCADE, related_name="debt_users")
    phone_number = models.CharField(max_length=15)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    profile_image = models.ImageField(upload_to='debtuser/profile/images', blank=True, null=True)

    transferred = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    accepted = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))

    currency = models.CharField(max_length=3, choices=CURRENCY, default='USD')
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('13000.00'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-balance']
        indexes = [
            models.Index(fields=['store']),
            models.Index(fields=['phone_number']),
        ]
        # OLD: unique_together = [['store', 'phone_number']]
        # NEW: faqat "o‘chirilmagan" (is_deleted=False) yozuvlar uchun unique
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'phone_number'],
                condition=Q(is_deleted=False),
                name='uniq_active_debtuser_phone_per_store',
            )
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"

    def recalculate_balance(self):
        base = self.documents.filter(is_deleted=False)
        transferred_usd = base.filter(method='transfer', currency='USD').aggregate(s=models.Sum('total_amount'))['s'] or Decimal('0.00')
        transferred_uzs = base.filter(method='transfer', currency='UZS').aggregate(s=models.Sum('total_amount'))['s'] or Decimal('0.00')
        accepted_usd    = base.filter(method='accept',   currency='USD').aggregate(s=models.Sum('total_amount'))['s'] or Decimal('0.00')
        accepted_uzs    = base.filter(method='accept',   currency='UZS').aggregate(s=models.Sum('total_amount'))['s'] or Decimal('0.00')

        if self.currency == 'USD':
            self.transferred = transferred_usd + (transferred_uzs / self.exchange_rate)
            self.accepted    = accepted_usd    + (accepted_uzs    / self.exchange_rate)
        else:
            self.transferred = transferred_uzs + (transferred_usd * self.exchange_rate)
            self.accepted    = accepted_uzs    + (accepted_usd    * self.exchange_rate)

        self.balance = self.transferred - self.accepted
        self.save(update_fields=['transferred', 'accepted', 'balance'])

    # --- Soft delete/restore ni hujjatlar bilan sinxron qilish (ixtiyoriy lekin tavsiya) ---
    def soft_delete(self):
        if self.is_deleted:
            return
        with transaction.atomic():
            # avval bog‘liq hujjatlarni soft-delete qilamiz (balans va kassa mantiqlari o‘zlarida bor)
            for doc in self.documents.select_for_update().filter(is_deleted=False):
                doc.soft_delete()
            super().soft_delete()

    def restore(self):
        if not self.is_deleted:
            return
        with transaction.atomic():
            super().restore()
            # istasangiz, hujjatlarni ham qayta tiklang:
            for doc in self.documents.select_for_update().filter(is_deleted=True):
                doc.restore()
            # tiklangandan keyin balans qayta hisob
            self.recalculate_balance()


class DebtDocument(SoftDeleteMixin, models.Model):
    debtuser = models.ForeignKey(DebtUser, on_delete=models.CASCADE, related_name='documents', blank=True, null=True)
    store = models.ForeignKey('store.Store', on_delete=models.CASCADE, related_name='debt_documents', null=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='debt_documents')
    is_mirror = models.BooleanField(default=False)

    # Yangi maydonlar
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)

    method = models.CharField(max_length=10, choices=DOCUMENT_METHOD, default='transfer')
    currency = models.CharField(max_length=3, choices=CURRENCY, default='USD')
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('13000.00'))

    cash_amount = models.DecimalField(max_digits=20, decimal_places=2)
    product_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    income = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))

    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']


    def clean(self):
        errors = {}

        if not self.store:
            errors["store"] = "Store majburiy."

        # Telefon yoki Debtor – ikkalasidan biri bo‘lishi shart
        if not (self.phone_number or self.debtuser_id):
            errors["phone_number"] = "Telefon yoki Debtor tanlang (kamida bittasi shart)."

        # Debtor tanlangan bo‘lsa, store mosligini tekshirib qo‘yamiz
        if self.debtuser_id and self.store_id and self.debtuser.store_id != self.store_id:
            errors["debtuser"] = "Tanlangan Debtor ushbu store’ga tegishli emas."

        if errors:
            raise ValidationError(errors)


    def _cash_amount_usd(self) -> Decimal:
        amt = self.cash_amount or Decimal('0')
        if self.currency == 'UZS':
            # 6 xonagacha aniqlik
            return (amt / (self.exchange_rate or Decimal('1'))).quantize(Decimal('0.000001'), ROUND_HALF_UP)
        return Decimal(str(amt)).quantize(Decimal('0.000001'), ROUND_HALF_UP)

    def _write_cashbox_txn(self):
        """create yoki update uchun tranzaksiyani sinxron tutish"""
        if not self.store or not hasattr(self.store, 'cashbox') or self.is_mirror:
            return

        amount_usd = self._cash_amount_usd()
        # Avval eski tranzaksiyalarni tozalaymiz (update bo‘lsa ham)
        # self.cash_debts.all().delete()
        self._delete_cash_debts_safely()

        if amount_usd > 0:
            is_out = (self.method == 'transfer')   # transfer -> chiqim, accept -> kirim
            note = f"Debt {self.method} #{self.pk or ''} - {self.phone_number or ''}"
            CashTransaction.objects.create(
                cashbox=self.store.cashbox,
                amount=amount_usd,
                is_out=is_out,
                note=note,
                debt_document=self
            )
    
    def assign_debtor(self):
        phone = (self.phone_number or "").strip()

        # Debtor yo‘q, lekin telefon bor -> telefon bo‘yicha debtorni topamiz/yaratamiz
        if not self.debtuser_id and self.store_id and phone:
            debtor, _ = DebtUser.objects.get_or_create(
                store=self.store,
                phone_number=phone,
                defaults={"first_name": self.first_name or "", "last_name": self.last_name or ""},
            )
            self.debtuser = debtor

        # Debtor bor, telefon bo‘sh bo‘lsa -> debtor’dan autofill
        if self.debtuser_id:
            if not self.phone_number:
                self.phone_number = self.debtuser.phone_number
            if not self.first_name:
                self.first_name = self.debtuser.first_name
            if not self.last_name:
                self.last_name = self.debtuser.last_name
            if not self.store_id:
                self.store = self.debtuser.store
    def _reverse_stock_for_delete(self):
        """
        Hujjatni o'chirganda zaxira harakatlarini teskari bajarish:
        - transfer: oldinda deduct_stock bo'lgan -> endi return_to_stock
        - accept:   oldinda return_to_stock bo'lgan -> endi deduct_stock
        """
        for dp in self.products.select_related('product').all():
            if not dp.product:
                continue
            if self.method == 'transfer':
                dp.return_to_stock()
            else:  # 'accept'
                dp.deduct_stock()

    def _apply_stock_for_restore(self):
        """
        Hujjatni qayta tiklaganda asl harakatlarni qayta qo'llash:
        - transfer: deduct_stock
        - accept:   return_to_stock
        """
        for dp in self.products.select_related('product').all():
            if not dp.product:
                continue
            if self.method == 'transfer':
                dp.deduct_stock()
            else:  # 'accept'
                dp.return_to_stock()
    
    def _delete_cash_debts_safely(self):
        for tx in self.cash_debts.all():
            tx.delete()  


    def save(self, *args, **kwargs):
        """
        - product_amount va total_amount ni hisoblaydi
        - tranzaksiyani kassa bilan sinxronlaydi (mirror bo‘lmasa)
        - yangi hujjatda debtor balansini yangilaydi
        """
        self.assign_debtor()
    # Endi validatsiya
        self.full_clean()
        
        # 1) Mahsulot summasi (agar hujjat allaqachon mavjud bo‘lsa — real bog‘liqlardan yig‘amiz)
        if self.pk:
            self.product_amount = sum(p.amount for p in self.products.all())
        else:
            self.product_amount = self.product_amount or Decimal('0.00')

        # 2) Jami
        self.total_amount = (self.cash_amount or Decimal('0')) + (self.product_amount or Decimal('0'))

        is_new = self._state.adding

        # with transaction.atomic():
        #     # Asosiy save
        #     super().save(*args, **kwargs)

        #     # 3) Cashbox bilan sinxron (mirror hujjat emasligi tekshiriladi)
        #     self._write_cashbox_txn()

        #     # 4) Yangi, non-mirror hujjatlarda balansni yangilash
        #     if is_new and not self.is_mirror and self.debtuser_id:
        #         self.debtuser.recalculate_balance()

        with transaction.atomic():
            super().save(*args, **kwargs)

            if not self.is_mirror and not self.is_deleted:
                self._write_cashbox_txn()
            else:
                self._delete_cash_debts_safely()

            if is_new and not self.is_mirror and self.debtuser_id:
                self.debtuser.recalculate_balance()

    def soft_delete(self):
        """
        Soft delete:
        - zaxira harakatini teskari bajarish
        - kassa tranzaksiyalarini o‘chirish
        - balance qayta hisoblash
        """
        if self.is_deleted:
            return
        with transaction.atomic():
            # 1) zaxirani teskari qilamiz
            self._reverse_stock_for_delete()

            # 2) flaglar
            self.is_deleted = True
            self.deleted_at = timezone.now()
            super().save(update_fields=['is_deleted', 'deleted_at'])

            # 3) kassani tozalash
            # self.cash_debts.all().delete()
            self._delete_cash_debts_safely()


            # 4) balansni yangilash
            if not self.is_mirror and self.debtuser_id:
                self.debtuser.recalculate_balance()

    def restore(self):
        """
        Restore:
        - asl zaxira harakatini qayta qo‘llash
        - kassa tranzaksiyasini qayta yaratish
        - balance qayta hisoblash
        """
        if not self.is_deleted:
            return
        with transaction.atomic():
            # 1) flaglar
            self.is_deleted = False
            self.deleted_at = None
            super().save(update_fields=['is_deleted', 'deleted_at'])

            # 2) zaxirani qayta qo‘llash
            self._apply_stock_for_restore()

            # 3) kassani qayta yozish
            self._write_cashbox_txn()

            # 4) balans
            if not self.is_mirror and self.debtuser_id:
                self.debtuser.recalculate_balance()

    # agar haqiqiy (hard) o'chirish kerak bo'lsa, CASCADE bo'yicha cash txn va products ketadi
    def hard_delete(self, *args, **kwargs):
        cb = getattr(getattr(self, 'store', None), 'cashbox', None)
        super().hard_delete(*args, **kwargs)
        if cb:
            cb.refresh_balance()

class DocumentProduct(models.Model):
    document = models.ForeignKey(DebtDocument, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)

    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))

    currency = models.CharField(max_length=3, choices=CURRENCY, default='USD')
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('13000.00'))

    income = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))

    def get_price_usd(self):
        if self.currency == 'UZS':
            return (self.price / self.exchange_rate).quantize(Decimal('0.000001'), ROUND_HALF_UP)
        return self.price or Decimal('0.00')

    def deduct_stock(self):
        if not self.product:
            return

        total_needed = self.quantity
        shelf_entries = self.product.stock_entries.filter(is_warehouse=False).order_by('created_at')

        for entry in shelf_entries:
            if total_needed <= 0:
                break
            deduct_qty = min(entry.quantity, total_needed)
            entry.quantity -= deduct_qty
            total_needed -= deduct_qty
            if entry.quantity <= 0:
                entry.delete()
            else:
                entry.save(update_fields=['quantity'])

        if total_needed > 0:
            StockTransfer.objects.create(
                product=self.product,
                quantity=total_needed,
                auto=True,
                note=f"Debt hujjat #{self.document_id} uchun avtomatik ko‘chirish"
            )

            shelf_entries = self.product.stock_entries.filter(is_warehouse=False).order_by('created_at')
            for entry in shelf_entries:
                if total_needed <= 0:
                    break
                deduct_qty = min(entry.quantity, total_needed)
                entry.quantity -= deduct_qty
                total_needed -= deduct_qty
                if entry.quantity <= 0:
                    entry.delete()
                else:
                    entry.save(update_fields=['quantity'])

        if total_needed > 0:
            raise ValueError(f"{self.product.name} uchun yetarli mahsulot yo‘q")

        self.product.recalculate_average_cost()

    def return_to_stock(self):

        if self.product:
            StockEntry.objects.create(
                product=self.product,
                quantity=self.quantity,
                unit_price = self.get_price_usd(),
                currency = 'USD',
                exchange_rate=self.exchange_rate,
                debt=self.document,
            )
            self.product.recalculate_average_cost()

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.price
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if self.document.is_mirror:
            return

        if is_new:
            if self.document.method == 'transfer':
                self.deduct_stock()
            elif self.document.method == 'accept':
                self.return_to_stock()
    def delete(self, *args, **kwargs):
        doc = self.document
        with transaction.atomic():
            if not doc.is_deleted:
                if doc.method == 'transfer':
                    self.return_to_stock()
                else:  # accept
                    self.deduct_stock()
            super().delete(*args, **kwargs)
            # summalarni va kassani sinxronlash uchun documentni saqlab qo'yamiz
            doc.save(update_fields=['product_amount', 'total_amount'])


class DebtImportOffer(models.Model):
    class Status(models.TextChoices):
        PENDING  = "pending",  "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        APPLIED  = "applied",  "Applied"
        EXPIRED  = "expired",  "Expired"

    debtor_user   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="debt_offers")
    created_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_debt_offers")
    status        = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    payload       = models.JSONField(default=dict)   # {amount, currency, phone_number, creditor_name, source_store_id, external_id, note, method?}
    idempotency_key = models.CharField(max_length=64, blank=True, null=True, unique=True)

    applied_store    = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, related_name="applied_debt_offers")
    applied_document = models.ForeignKey(DebtDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="from_offers")

    created_at    = models.DateTimeField(auto_now_add=True)
    expires_at    = models.DateTimeField(null=True, blank=True)
    decided_at    = models.DateTimeField(null=True, blank=True)
    decided_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="decided_debt_offers")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Offer #{self.pk} → {self.debtor_user} [{self.status}]"

    # ---- domain helpers ----
    def is_pending(self) -> bool:
        if self.status != self.Status.PENDING:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def mark(self, status: str, by=None):
        self.status = status
        self.decided_at = timezone.now()
        if by:
            self.decided_by = by
        self.save(update_fields=["status", "decided_at", "decided_by"])

    def apply_to_store(self, store: Store, actor) -> DebtDocument:
        """
        Materialize the debt into the chosen store.
        - Ensures/creates DebtUser for the counterparty (creditor) in the store
        - Creates a DebtDocument (default: method='transfer')
        - Recalculates balances
        """
        if not self.is_pending() and self.status != self.Status.ACCEPTED:
            # Idempotent return if already applied
            if self.status == self.Status.APPLIED and self.applied_document_id:
                return self.applied_document
            raise ValueError("Offer is not pending/accepted.")

        amount   = self.payload.get("amount")
        currency = self.payload.get("currency", "USD")
        phone    = self.payload.get("phone_number")  # creditor/customer phone (counterparty in that store)
        name     = self.payload.get("creditor_name", "")
        method   = self.payload.get("method") or "transfer"  # keep consistent with your math transferred-accepted

        if not amount:
            raise ValueError("Offer payload missing 'amount'")

        # 1) Ensure a DebtUser for this counterparty in the chosen store
        du, _ = DebtUser.objects.get_or_create(
            store=store,
            phone_number=phone or f"unknown-{self.pk}",
            defaults={
                "first_name": name or "Unknown",
                "last_name": "",
                "currency": currency,
            }
        )

        # 2) Create the debt document in that store
        doc = DebtDocument.objects.create(
            debtuser=du,
            owner=actor,                      # who accepted the offer
            method=method,                    # usually 'transfer' for “we gave debt”
            currency=currency,
            cash_amount=amount,
            product_amount=0,
            total_amount=amount,
            is_mirror=False,
            date=timezone.now(),
        )

        # 3) Recalculate balance
        du.recalculate_balance()

        # 4) Link + mark applied
        self.applied_store = store
        self.applied_document = doc
        self.mark(self.Status.APPLIED, by=actor)
        self.save(update_fields=["applied_store", "applied_document"])
        return doc

