from decimal import Decimal
from django.db import models

from platform_user.models import PlatformUser


class Store(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(PlatformUser, on_delete=models.CASCADE, related_name='owned_shops')
    description = models.TextField(blank=True, null=True)

    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    logo = models.ImageField(upload_to='shops/logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='shops/banners/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_balance(self):
        return self.cashbox.balance if hasattr(self, 'cashbox') else Decimal('0.00')
