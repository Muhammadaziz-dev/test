from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from product.models import StockEntry, WasteEntry
from order.models import ProductOrder
from django.core.validators import MinValueValidator, MinLengthValidator
from loan.models import DocumentProduct, DebtDocument, DebtUser 
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

REASON_TYPES = [
    ("UNUSABLE", "Yaroqsiz"),
    ("DISLIKED", "Yoqmagan"),
    ("OTHER", "Boshqa"),
]

def validate_reason_type(value):
    valid_choices = [choice[0] for choice in REASON_TYPES]
    if value not in valid_choices:
        raise ValidationError("Noto'g'ri sabab turi")

class Refund(models.Model):
    product_order = models.ForeignKey(
        ProductOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds'
    )
    document_product = models.ForeignKey(
        DocumentProduct, null=True, blank=True, on_delete=models.SET_NULL, related_name='refunds'
    )
    reason_type = models.CharField(max_length=200, choices=REASON_TYPES, validators=[validate_reason_type])
    custom_reason = models.CharField(max_length=200, null=True, blank=True, validators=[
            MinLengthValidator(5, "Sabab kamida 5 ta belgidan iborat bo'lishi kerak")
        ])
    quantity = models.PositiveSmallIntegerField(validators=[
            MinValueValidator(1, "Kamida 1 dona mahsulotni qaytarish kerak")
        ])
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def clean(self):
        # 1) Bitta atigi one of them bo'lsin
        if bool(self.product_order) == bool(self.document_product):
            raise ValidationError("Faqat bitta: order yoki debt document_product bo'lishi kerak")

        # 2) OTHER uchun custom_reason majburiy
        if self.reason_type == "OTHER" and not self.custom_reason:
            raise ValidationError("Boshqa sababni yozishingiz shart")

        # 3) mavjud miqdor tekshiruvi
        if self.product_order:
            prev = self.product_order.refunds.exclude(pk=self.pk).aggregate(
                s=models.Sum('quantity'))['s'] or 0
            available = self.product_order.quantity - prev
            if self.quantity > available:
                raise ValidationError(f"Order refund uchun qaytarishga {available} dona qoldi")
        elif self.document_product:
            dp = self.document_product
            prev = dp.refunds.exclude(pk=self.pk).aggregate(
                s=models.Sum('quantity'))['s'] or 0
            available = dp.quantity - prev
            if self.quantity > available:
                raise ValidationError(f"Debt hujjat uchun qaytarishga {available} dona qoldi")

    def delete(self, *args, **kwargs):
        # Refundni o'chirishni cheklash
        if self.created_at < timezone.now() - timezone.timedelta(days=1):
            raise ValidationError("Faqlat so'nggi 24 soat ichidagi refundlarni o'chirish mumkin")
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self._state.adding

        with transaction.atomic():
            # 1) Avval parentni saqlab pk olamiz
            super().save(*args, **kwargs)

            # 2) ORDER tomoni (birinchi marta yaratilganda)
            if self.product_order and is_new:
                product = self.product_order.product

                if self.reason_type in ("DISLIKED", "OTHER"):
                    # Stockka qaytarish
                    StockEntry.objects.create(
                        product=product,
                        quantity=self.quantity,
                        unit_price=product.enter_price,
                        currency="USD",
                        exchange_rate=self.product_order.exchange_rate,
                    )
                    product.recalculate_average_cost()
                else:  # UNUSABLE -> Waste
                    WasteEntry.objects.create(
                        product=product,
                        quantity=self.quantity,
                        refund=self,  # endi self.pk bor!
                        reason=f"{self.get_reason_type_display()} {self.custom_reason or ''}"
                    )

            # 3) DEBT tomoni (birinchi marta yaratilganda)
            if self.document_product and is_new:
                dp = self.document_product

                # 3.1) miqdorni kamaytirish
                dp.quantity -= self.quantity
                dp.save(update_fields=['quantity'])

                # 3.2) zaxiraga qaytarish / waste
                if self.reason_type in ("DISLIKED", "OTHER"):
                    StockEntry.objects.create(
                        product=dp.product,
                        quantity=self.quantity,
                        unit_price=dp.product.enter_price,
                        currency=dp.currency,
                        exchange_rate=dp.exchange_rate,
                        debt=dp.document,
                    )
                    dp.product.recalculate_average_cost()
                else:  # UNUSABLE -> Waste
                    WasteEntry.objects.create(
                        product=dp.product,
                        quantity=self.quantity,
                        refund=self,  # endi self.pk bor!
                        reason=f"{self.get_reason_type_display()} {self.custom_reason or ''}"
                    )

                # 3.3) hujjat summalarini yangilash
                doc: DebtDocument = dp.document
                doc.product_amount = doc.products.aggregate(s=models.Sum('amount'))['s'] or Decimal('0.00')
                doc.total_amount = (doc.cash_amount or Decimal('0.00')) + doc.product_amount
                doc.save(update_fields=['product_amount', 'total_amount'])

                # 3.4) balansni yangilash
                if doc.debtuser_id:
                    doc.debtuser.recalculate_balance()

    def refund_price(self):
        return self.product_order.get_price_usd() * self.quantity if self.product_order else Decimal("0.00")

    def __str__(self):
        if self.product_order:
            return f"Refund: {self.quantity} x {self.product_order.product.name}"
        elif self.document_product:
            return f"Refund: {self.quantity} x {self.document_product.product.name}"
        return "Refund: Unknown product"