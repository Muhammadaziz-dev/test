from django.db import models
from accounts.models import CustomUser

WHICH = [
    ('platform', 'Platform'),
    ('e-commerce', 'E-Commerce')
]


class Device(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="devices")

    device_type = models.CharField(max_length=30)
    os = models.CharField(max_length=50)
    browser = models.CharField(max_length=50)
    brand = models.CharField(max_length=50, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)

    where = models.CharField(max_length=100, default="platform", choices=WHICH)

    ip_address = models.GenericIPAddressField(blank=True, null=True)
    last_login = models.DateTimeField(auto_now=True)

    refresh_token = models.CharField(max_length=500, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Qurilma"
        verbose_name_plural = "Qurilmalar"
        ordering = ['-last_login']

    def __str__(self):
        return f"{self.user.phone_number} — {self.device_type} ({self.os})"