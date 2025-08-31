# models.py
from decimal import Decimal, ROUND_HALF_UP
import math
from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.files.base import ContentFile
from PIL import Image as PILImage
from io import BytesIO
import re
from django_currentuser.middleware import get_current_authenticated_user

from accounts.models import CustomUser
from category.models import Category
from platform_user.exchange import get_default_exchange_rate


# validatorlar

def validate_finite(value):
    if isinstance(value, float) and (math.isnan(value) or not math.isfinite(value)):
        raise ValueError("Value must be a finite number.")
    if isinstance(value, Decimal) and (value.is_nan() or not value.is_finite()):
        raise ValueError("Value must be a finite number.")


def validate_barcode(value):
    if value and (len(value) != 13 or not value.isdigit()):
        raise ValidationError("Barcode 13 ta raqamdan iborat bo'lishi kerak")

    # Checksum validatsiyasi
    digits = [int(d) for d in value]
    total = sum(d if i % 2 == 0 else d * 3 for i, d in enumerate(digits[:12]))
    check = (10 - (total % 10)) % 10
    if check != digits[12]:
        raise ValidationError("Noto'g'ri barcode checksum")


def validate_positive(value):
    if value < 0:
        raise ValidationError("Qiymat manfiy bo'lishi mumkin emas")


def validate_sku(value):
    if value and not re.match(r'^SKU-[A-Z0-9]{8}$', value):
        raise ValidationError("Noto'g'ri SKU formati. Format: SKU-XXXXXXXX")


def validate_image_size(image):
    max_size = 5 * 1024 * 1024  # 5 MB
    if image and image.size > max_size:
        raise ValidationError("Rasm hajmi 5MB dan oshmasligi kerak.")


image_validators = [FileExtensionValidator(['jpg', 'jpeg', 'png']), validate_image_size]
video_validators = [FileExtensionValidator(['mp4', 'mov', 'avi'])]

COUNT_TYPE_CHOICES = [
    ('PCS', 'Pieces'), ('KG', 'Kilogram'), ('L', 'Liter'), ('M', 'Meter'),
    ('BOX', 'Box'), ('SET', 'Set'), ('PKG', 'Package'), ('D', 'Dozen')
]

from django.db import models
from django.contrib.auth import get_user_model


class ExportTaskLog(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('PROCESSING', 'Jarayonda'),
        ('SUCCESS', 'Tayyor'),
        ('FAILED', 'Xato'),
    ]

    task_id = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    store_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    file_url = models.CharField(max_length=1000, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    progress = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.store_id} ({self.status})"


class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        if not self.is_deleted:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_deleted', 'deleted_at'])

    def delete(self, *args, **kwargs):
        self.soft_delete()

    def hard_delete(self):
        super().delete()

    def restore(self):
        if self.is_deleted:
            self.is_deleted = False
            self.deleted_at = None
            self.save(update_fields=['is_deleted', 'deleted_at'])


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def all_objects(self):
        return self.get_queryset()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)


class Product(SoftDeleteMixin, models.Model):
    CURRENCY_CHOICES = [('USD', 'USD'), ('UZS', 'UZS')]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    store = models.ForeignKey('store.Store', on_delete=models.CASCADE, related_name='products', null=True)
    enter_price = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0'),
                                      validators=[validate_finite])
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True, validators=[validate_sku])
    barcode = models.CharField(max_length=13, unique=True, blank=True, null=True, validators=[validate_barcode])
    count_type = models.CharField(max_length=10, choices=COUNT_TYPE_CHOICES, default='PCS')
    date_added = models.DateField(auto_now_add=True)

    count = models.IntegerField(default=0, validators=[validate_positive])
    warehouse_count = models.IntegerField(default=0, validators=[validate_positive])

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True, db_index=True)

    out_price = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0'),
                                    validators=[validate_finite, validate_positive])
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='USD')
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0'),
                                        validators=[MinValueValidator(Decimal('0.000000'))])

    in_stock = models.BooleanField(default=True)

    objects = ProductManager()
    all_objects = AllObjectsManager()

    def clean(self):
        super().clean()
        enter_price = self.enter_price
        out_price = self.out_price

        if enter_price > out_price:
            raise ValidationError("Sotish narxi kirish narxidan kam bo'lishi mumkin emas")

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        indexes = [
            models.Index(fields=['name', 'sku', 'barcode']),
            models.Index(fields=['store', 'is_deleted']),
        ]

    def set_default_exchange_rate(self):
        if not self.exchange_rate or self.exchange_rate <= 1:
            cache_key = f'exchange_rate_{self.currency}'
            self.exchange_rate = cache.get(cache_key)
            if not self.exchange_rate:
                user = get_current_authenticated_user()
                if user:
                    self.exchange_rate = get_default_exchange_rate(user)
                    cache.set(cache_key, self.exchange_rate, 3600)

    def generate_sku(self):
        if not self.sku:
            self.sku = 'SKU-' + get_random_string(8, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

    def generate_barcode(self):
        if not self.barcode:
            base = get_random_string(12, '0123456789')
            digits = [int(x) for x in base]
            total = sum(d if i % 2 == 0 else d * 3 for i, d in enumerate(digits))
            check = (10 - (total % 10)) % 10
            self.barcode = base + str(check)

    def normalize_currency(self):
        if self.currency == "UZS":
            self.out_price = (self.out_price / self.exchange_rate).quantize(Decimal('0.000001'), ROUND_HALF_UP)
            self.currency = "USD"

    def save(self, *args, **kwargs):
        self.set_default_exchange_rate()

        self.normalize_currency()

        self.generate_sku()
        self.generate_barcode()

        super().save(*args, **kwargs)
        cache.set(f'product_{self.pk}', self, 3600)

    def recalculate_average_cost(self, update=True):
        from django.db.models import Sum, F, Q, Min
        from django.db import transaction
        from decimal import Decimal

        with transaction.atomic():
            groups = self.stock_entries.values(
                'unit_price', 'currency', 'exchange_rate', 'is_warehouse'
            ).annotate(
                total_quantity=Sum('quantity'),
                min_id=Min('id')
            )

            for group in groups:
                self.stock_entries.filter(id=group['min_id']).update(
                    quantity=group['total_quantity']
                )

                self.stock_entries.filter(
                    unit_price=group['unit_price'],
                    currency=group['currency'],
                    exchange_rate=group['exchange_rate'],
                    is_warehouse=group['is_warehouse']
                ).exclude(id=group['min_id']).delete()

        aggregates = self.stock_entries.aggregate(
            total_qty=Sum('quantity', output_field=models.DecimalField(max_digits=40, decimal_places=6)),
            total_cost=Sum(F('quantity') * F('unit_price'),
                           output_field=models.DecimalField(max_digits=40, decimal_places=6)),
            shelf_qty=Sum('quantity', filter=Q(is_warehouse=False), default=0),
            warehouse_qty=Sum('quantity', filter=Q(is_warehouse=True), default=0)
        )

        total_qty = aggregates['total_qty'] or Decimal('0')
        total_cost = aggregates['total_cost'] or Decimal('0')
        shelf_qty = aggregates['shelf_qty'] or 0
        warehouse_qty = aggregates['warehouse_qty'] or 0

        avg_cost = (total_cost / total_qty).quantize(Decimal('0.000001'), ROUND_HALF_UP) if total_qty > 0 else Decimal(
            '0')

        self.count = shelf_qty
        self.warehouse_count = warehouse_qty
        self.enter_price = avg_cost

        if update:
            Product.objects.filter(pk=self.pk).update(
                count=shelf_qty,
                warehouse_count=warehouse_qty,
                enter_price=avg_cost
            )
            cache.delete(f'product_{self.pk}')

    def __str__(self):
        return f"#{self.pk} {self.name} - {self.count}"


class StockEntry(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_entries')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1, "Kamida 1 dona ko'rsatilishi kerak")])
    unit_price = models.DecimalField(max_digits=20, decimal_places=6,
                                     validators=[validate_finite, MinValueValidator(Decimal('0.000001'))])
    currency = models.CharField(max_length=3, choices=Product.CURRENCY_CHOICES, default='USD')
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1.0'),
                                        validators=[MinValueValidator(Decimal('0.000001'))])
    created_at = models.DateTimeField(auto_now_add=True)
    is_warehouse = models.BooleanField(default=False)
    debt = models.ForeignKey("loan.DebtDocument", blank=True, null=True, on_delete=models.SET_NULL, related_name="stock_entries")
    
    class Meta:
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.exchange_rate or self.exchange_rate <= 1:
            cache_key = f'exchange_rate_{self.currency}'
            self.exchange_rate = cache.get(cache_key)
            if not self.exchange_rate:
                user = get_current_authenticated_user()
                if user:
                    self.exchange_rate = get_default_exchange_rate(user)
                    cache.set(cache_key, self.exchange_rate, 3600)

        if self.currency == "UZS":
            self.unit_price = (self.unit_price / self.exchange_rate).quantize(Decimal('0.000001'), ROUND_HALF_UP)
            self.currency = "USD"

        is_new = self._state.adding
        super().save(*args, **kwargs)

        self.product.recalculate_average_cost()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.product.recalculate_average_cost()


class WasteEntry(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='waste_entries')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1, "Kamida 1 dona ko'rsatilishi kerak")])
    reason = models.CharField(max_length=255, default="Yaroqsiz holat")
    refund = models.ForeignKey("refund.Refund", on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="waste_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} — {self.quantity} dona yo‘qotilgan"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product/images/', validators=image_validators)
    thumbnail = models.ImageField(upload_to='product/thumbnails/', null=True, blank=True)

    def __str__(self):
        return self.product.name if self.product else "Image"


    def generate_thumbnail(self):
        if not self.image:
            return

        try:
            img = PILImage.open(self.image)
            img.thumbnail((60, 60))

            thumb_io = BytesIO()
            img.save(thumb_io, format='PNG', quality=85)
            thumb_file = ContentFile(thumb_io.getvalue())

            thumb_name = f'thumb_{self.image.name.split("/")[-1]}'
            self.thumbnail.save(thumb_name, thumb_file, save=False)
        except Exception as e:
            print(f"Thumbnail generation error: {e}")

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if not self.pk or (update_fields is None or 'image' in update_fields):
            self.generate_thumbnail()

        super().save(*args, **kwargs)


class Properties(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="properties")
    feature = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Properties"
        indexes = [
            models.Index(fields=['product', 'feature']),
        ]

    def __str__(self):
        return self.feature
