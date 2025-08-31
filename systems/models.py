from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction

from cashbox.service import CashboxService
from platform_user.exchange import get_default_exchange_rate
from product.models import Product, StockEntry
from django.core.exceptions import ValidationError

from store.models import Store


class StockTransfer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transfer_logs')
    quantity = models.PositiveIntegerField()
    auto = models.BooleanField(default=False)
    note = models.CharField(
        max_length=255,
        blank=True,
        help_text="Sabab yoki izoh (masalan: avtomatik, qo‘lda)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Ombordan rastaga o'tkazma"
        verbose_name_plural = "Ombordan rastaga o'tkazmalar"

    def __str__(self):
        return f"{self.product.name} — {self.quantity} dona ombordan rastaga"

    def save(self, *args, **kwargs):
        self.perform_transfer()

        super().save(*args, **kwargs)

    def reverse_transfer(self):
        if self.quantity <= 0:
            raise ValidationError("Miqdor musbat bo‘lishi kerak")

        quantity_to_restore = self.quantity
        shelf_entries = self.product.stock_entries.filter(is_warehouse=False).order_by('created_at')

        with transaction.atomic():
            for entry in shelf_entries:
                if quantity_to_restore <= 0:
                    break

                deduct_qty = min(entry.quantity, quantity_to_restore)
                unit_price = entry.unit_price
                exchange_rate = entry.exchange_rate

                entry.quantity -= deduct_qty
                quantity_to_restore -= deduct_qty

                if entry.quantity <= 0:
                    entry.delete()
                else:
                    entry.save(update_fields=['quantity'])

                StockEntry.objects.create(
                    product=self.product,
                    quantity=deduct_qty,
                    unit_price=unit_price,
                    currency="USD",
                    exchange_rate=exchange_rate,
                    is_warehouse=True
                )

            self.product.recalculate_average_cost()

    def perform_transfer(self):
        if self.quantity <= 0:
            raise ValidationError("Miqdor musbat bo‘lishi kerak")

        quantity_to_transfer = self.quantity
        warehouse_entries = self.product.stock_entries.filter(is_warehouse=True).order_by('created_at')

        total_available = warehouse_entries.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        if total_available < self.quantity:
            raise ValidationError(f"Omborda {self.product.name} uchun yetarli mahsulot yo‘q.")

        with transaction.atomic():
            for entry in warehouse_entries:
                if quantity_to_transfer <= 0:
                    break

                deduct_qty = min(entry.quantity, quantity_to_transfer)
                entry.quantity -= deduct_qty
                if entry.quantity <= 0:
                    entry.delete()
                else:
                    entry.save(update_fields=['quantity'])

                StockEntry.objects.create(
                    product=self.product,
                    quantity=deduct_qty,
                    unit_price=entry.unit_price,
                    currency="USD",
                    exchange_rate=entry.exchange_rate,
                    is_warehouse=False
                )

                quantity_to_transfer -= deduct_qty

            self.product.recalculate_average_cost()

    def delete(self, *args, **kwargs):
        self.reverse_transfer()
        print("delete stock")
        super().delete(*args, **kwargs)


class ProductSale(models.Model):
    order = models.ForeignKey("order.Order", on_delete=models.CASCADE, related_name='sales')
    product = models.ForeignKey("product.Product", on_delete=models.CASCADE, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=20, decimal_places=6)
    total_price = models.DecimalField(max_digits=20, decimal_places=6)
    profit = models.DecimalField(max_digits=20, decimal_places=6)

    currency = models.CharField(max_length=3, choices=[('USD', 'USD'), ('UZS', 'UZS')], default='USD')
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mahsulot sotuvi"
        verbose_name_plural = "Mahsulot sotuvlari"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product} × {self.quantity} ({self.unit_price} USD)"


class ProductEntrySystem(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    count = models.PositiveIntegerField(default=0)
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True
    )
    store = models.ForeignKey('store.Store', on_delete=models.CASCADE, related_name='products_imports', null=True)
    unit_price = models.DecimalField(max_digits=20, decimal_places=6)
    currency = models.CharField(max_length=3, choices=[("USD", "USD"), ("UZS", "UZS")])
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1.0'))
    is_warehouse = models.BooleanField(default=False)

    def get_price_usd(self):
        if self.currency == "UZS":
            return (self.unit_price / self.exchange_rate).quantize(Decimal("0.000001"), ROUND_HALF_UP)
        return self.unit_price

    def save(self, *args, **kwargs):
        if not self.exchange_rate or self.exchange_rate <= 1:
            from django_currentuser.middleware import get_current_authenticated_user
            user = get_current_authenticated_user()
            if user:
                self.exchange_rate = get_default_exchange_rate(user)

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.product and self.count > 0:
            self.import_to_stock()

        if is_new:
            CashboxService.expense(
                cashbox=self.product.store.cashbox,
                amount=(self.unit_price * self.count),
                note=f"Mahsulot importi #{self.pk} uchun to'lov",
                rate=self.exchange_rate,
                entry_system=self
            )

    def import_to_stock(self):
        price_usd = self.get_price_usd()

        last_stock = self.product.stock_entries.filter(
            is_warehouse=self.is_warehouse,
            unit_price=price_usd,
            currency="USD"
        ).order_by('-created_at').first()

        if last_stock:
            last_stock.quantity += self.count
            last_stock.save(update_fields=['quantity'])
        else:
            StockEntry.objects.create(
                product=self.product,
                quantity=self.count,
                unit_price=self.unit_price,
                currency=self.product.currency,
                exchange_rate=self.exchange_rate,
                is_warehouse=self.is_warehouse
            )

        self.product.recalculate_average_cost()

    def delete(self, *args, **kwargs):
        quantity_to_deduct = self.count
        price_usd = self.get_price_usd()

        stock_entries = self.product.stock_entries.filter(
            is_warehouse=self.is_warehouse,
            unit_price=price_usd,
            currency="USD"
        ).order_by('created_at')

        with transaction.atomic():
            for entry in stock_entries:
                if quantity_to_deduct <= 0:
                    break

                deduct_qty = min(entry.quantity, quantity_to_deduct)
                entry.quantity -= deduct_qty
                quantity_to_deduct -= deduct_qty

                if entry.quantity <= 0:
                    entry.delete()
                else:
                    entry.save(update_fields=['quantity'])

            self.product.recalculate_average_cost()

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Entry {self.count}×{self.product} on {self.date}"
