import math
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.db import models, transaction
from django.utils import timezone

from platform_user.exchange import get_default_exchange_rate
from store_user.models import StoreUser
from product.models import Product, StockEntry
from systems.models import StockTransfer, ProductSale
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class OrderManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.soft_delete()

    def soft_delete(self):
        if not self.is_deleted:
            for item in self.items.select_related('product'):
                item.return_to_stock()
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


phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{9,15}$',
    message="Telefon raqami 998901234567 formatida bo'lishi kerak"
)


def validate_finite(value):
    if isinstance(value, float) and (math.isnan(value) or not math.isfinite(value)):
        raise ValidationError("Qiymat cheksiz yoki noto'g'ri formatda")
    if isinstance(value, Decimal) and (value.is_nan() or not value.is_finite()):
        raise ValidationError("Qiymat cheksiz yoki noto'g'ri formatda")


class Order(SoftDeleteMixin, models.Model):
    store = models.ForeignKey("store.Store", on_delete=models.CASCADE, related_name="orders", null=True)
    owner = models.ForeignKey('platform_user.PlatformUser', null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")
    customer = models.ForeignKey(StoreUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    phone_number = models.CharField(max_length=15, validators=[phone_validator])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1.0'), validators=[
        MinValueValidator(Decimal('0.000001'), "Ayirboshlash kursi 0 dan katta bo'lishi kerak"),
        validate_finite
    ])
    currency = models.CharField(max_length=10, default='USD')
    payment_type = models.CharField(max_length=10, choices=[("cash", "Cash"), ("card", "Card")], default='cash')

    total_price = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True,
                                      validators=[validate_finite])
    total_profit = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True, validators=[
        MinValueValidator(Decimal('0.000001'), "To'lov miqdori 0 dan katta bo'lishi kerak"),
        validate_finite
    ])
    change_given = models.BooleanField(default=False)
    currency_change = models.CharField(max_length=10, default='USD')
    change_amount = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True, validators=[
        MinValueValidator(Decimal('0'), "Qaytim miqdori manfiy bo'lishi mumkin emas"),
        validate_finite
    ])

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    objects = OrderManager()
    all_objects = AllObjectsManager()

    def clean(self):
        super().clean()

        if self.change_given:
            if self.change_amount is None:
                raise ValidationError("Qaytim berilgan bo'lsa, qaytim miqdori kiritilishi shart.")

            if self.currency_change != self.currency:
                raise ValidationError("Qaytim valyutasi buyurtma valyutasi bilan bir xil bo'lishi kerak")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"

    def __str__(self):
        return f"Order #{self.pk} — {self.phone_number}"

    def assign_customer(self):
        self.customer, _ = StoreUser.objects.get_or_create(
            phone_number=self.phone_number,
            defaults={'first_name': self.first_name, 'last_name': self.last_name}
        )

    def calculate_totals_and_change(self):
        total = Decimal('0.00')
        enter_price = Decimal('0.00')
        payment = Decimal('0.00')
        income = Decimal('0.00')
        d_income = Decimal('0.00')

        for item in self.items.select_related('product'):
            if not item.product:
                continue
            sale_price = item.get_price_usd()
            cost = item.product.enter_price or Decimal("0")
            total += sale_price * item.quantity
            enter_price += cost * item.quantity
            d_income += (sale_price - cost) * item.quantity

        self.total_price = total.quantize(Decimal('0.000000'), ROUND_HALF_UP)

        if self.paid_amount is not None:
            paid = self.paid_amount
            if self.currency == "UZS":
                paid = (paid / self.exchange_rate).quantize(Decimal("0.000001"), ROUND_HALF_UP)
                self.currency = "USD"
            self.paid_amount = paid
            payment += paid

            if self.change_given:
                change = self.change_amount or Decimal("0")
                if self.currency_change == "UZS":
                    change = (change / self.exchange_rate).quantize(Decimal("0.000001"), ROUND_HALF_UP)
                    self.currency_change = "USD"
                self.change_amount = change

                payment -= change
                income += payment - enter_price
            else:
                income += d_income + (payment - total)

        self.total_profit = income.quantize(Decimal("0.000001"), ROUND_HALF_UP)
    
    def soft_delete(self):
        if not self.is_deleted:
            # Avval zaxiraga qaytarish
            for item in self.items.select_related('product'):
                item.return_to_stock()

            # Kassadagi bog‘liq yozuvlarni o‘chirish (CashTransaction orqali)
            if hasattr(self.store, 'cashbox'):
                for tx in self.store.cashbox.transactions.filter(order=self):
                    tx.delete()  # hook ishlaydi va balans refresh bo‘ladi

            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_deleted', 'deleted_at'])


    def restore(self):
        if self.is_deleted:
            # Zaxiradan chiqarish (ProductOrder.deduct_stock())
            for item in self.items.select_related('product'):
                item.deduct_stock()

            # Kassaga qayta yozish
            if hasattr(self.store, 'cashbox') and self.paid_amount:
                from cashbox.service import CashboxService
                CashboxService.income(
                    cashbox=self.store.cashbox,
                    amount=self.paid_amount,
                    note=f"Buyurtma #{self.pk} uchun to‘lov",
                    order=self,
                    rate=self.exchange_rate
                )
                if self.change_given and self.change_amount:
                    CashboxService.expense(
                        cashbox=self.store.cashbox,
                        amount=self.change_amount,
                        note=f"Buyurtma #{self.pk} qaytim",
                        order=self,
                        rate=self.exchange_rate,
                    )

            self.is_deleted = False
            self.deleted_at = None
            self.save(update_fields=['is_deleted', 'deleted_at'])

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if not self.exchange_rate or self.exchange_rate <= 1:
            from django_currentuser.middleware import get_current_authenticated_user
            user = get_current_authenticated_user()
            if user:
                self.exchange_rate = get_default_exchange_rate(user)

        with transaction.atomic():
            self.assign_customer()
            super().save(*args, **kwargs)

            self.calculate_totals_and_change()
            super().save(update_fields=['total_price', 'total_profit', 'change_amount', 'currency', 'paid_amount'])

            if is_new and self.store and self.paid_amount:
                from cashbox.service import CashboxService

                CashboxService.income(
                    cashbox=self.store.cashbox,
                    amount=self.paid_amount,
                    note=f"Buyurtma #{self.pk} uchun to‘lov",
                    order=self,
                    rate = self.exchange_rate,
                )

                if self.change_given and self.change_amount:
                    CashboxService.expense(
                        cashbox=self.store.cashbox,
                        amount=self.change_amount,
                        note=f"Buyurtma #{self.pk} qaytim",
                        rate=self.exchange_rate,
                        order=self
                    )

    @property
    def unreturned_income(self):
        try:
            paid = self.paid_amount or Decimal("0.00")
            total = self.total_price or Decimal("0.00")
            change = self.change_amount or Decimal("0.00")
            remainder = paid - total - change
            return remainder.quantize(Decimal('0.000001'), ROUND_HALF_UP)
        except (InvalidOperation, TypeError):
            return Decimal("0.00")


class ProductOrder(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    quantity = models.PositiveIntegerField(validators=[
        MinValueValidator(1, "Kamida 1 dona mahsulot buyurtma qilinishi kerak")
    ])
    price = models.DecimalField(max_digits=20, decimal_places=6, validators=[
        MinValueValidator(Decimal('0.000001'), "Narx 0 dan katta bo'lishi kerak"),
        validate_finite
    ])
    currency = models.CharField(max_length=3, choices=[("USD", "USD"), ("UZS", "UZS")], default="USD")
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1.0'), validators=[
        MinValueValidator(Decimal('0.000001'), "Ayirboshlash kursi 0 dan katta bo'lishi kerak"),
        validate_finite
    ])

    def clean(self):
        super().clean()

        if self.product and self.quantity > 0:
            available = self.product.count + self.product.warehouse_count
            if available < self.quantity:
                raise ValidationError(
                    f"Yetarli mahsulot mavjud emas. Sotish uchun {available} dona bor, siz {self.quantity} dona so'rayapsiz."
                )

    def __str__(self):
        return f"{self.product} × {self.quantity}"

    class Meta:
        verbose_name = "Buyurtmadagi Mahsulot"
        verbose_name_plural = "Buyurtmadagi Mahsulotlar"

    def get_price_usd(self):
        if self.currency == 'UZS':
            try:
                return (self.price / self.exchange_rate).quantize(Decimal('0.000001'), ROUND_HALF_UP)
            except (TypeError, ZeroDivisionError):
                return Decimal("0")
        return self.price or Decimal("0")

    def return_to_stock(self):
        if self.product:
            StockEntry.objects.create(
                product=self.product,
                quantity=self.quantity,
                unit_price=self.product.enter_price,
                currency="USD",
                exchange_rate=self.exchange_rate,
            )
            self.product.recalculate_average_cost()

    def deduct_stock(self):
        if not self.product:
            return

        total_needed = self.quantity
        shelf_entries = self.product.stock_entries.filter(is_warehouse=False).order_by('created_at')
        warehouse_entries = self.product.stock_entries.filter(is_warehouse=True).order_by('created_at')

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
                note="Buyurtma uchun avtomatik ko‘chirish"
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
            raise ValueError(f"{self.product.name} mahsuloti uchun yetarli zahira yo‘q")

        self.product.recalculate_average_cost()

    def save(self, *args, **kwargs):
        if not self.exchange_rate or self.exchange_rate <= 1:
            from django_currentuser.middleware import get_current_authenticated_user
            user = get_current_authenticated_user()
            if user:
                self.exchange_rate = get_default_exchange_rate(user)

        with transaction.atomic():
            is_new = self._state.adding
            if self.currency == "UZS":
                self.price = (self.price / self.exchange_rate).quantize(Decimal('0.000001'), ROUND_HALF_UP)
                self.currency = "USD"
            super().save(*args, **kwargs)

            if is_new and self.product:
                self.deduct_stock()

                ProductSale.objects.create(
                    order=self.order,
                    product=self.product,
                    quantity=self.quantity,
                    unit_price=self.get_price_usd(),
                    total_price=self.get_price_usd() * self.quantity,
                    profit=(self.get_price_usd() - self.product.enter_price) * self.quantity,
                    currency="USD",
                    exchange_rate=self.exchange_rate
                )
            if self.order:
                self.order.calculate_totals_and_change()
                self.order.save(update_fields=['total_price', 'total_profit', 'change_amount'])

    def delete(self, *args, **kwargs):
        self.return_to_stock()
        super().delete(*args, **kwargs)
