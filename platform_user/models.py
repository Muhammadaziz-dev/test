from django.db import models
from accounts.models import CustomUser


class PlatformUser(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='platform_profile'
    )
    chief = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subordinates')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Platforma foydalanuvchisi"
        verbose_name_plural = "Platforma foydalanuvchilari"
        ordering = ['-created_at']

    def __str__(self):
        return self.user.username or self.user.phone_number

    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"


class RateUsd(models.Model):
    user = models.OneToOneField(
        PlatformUser,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='usd_rate'
    )
    rate = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        default=0
    )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "USD Kursi"
        verbose_name_plural = "USD Kurslari"

    def __str__(self):
        return f"{self.user.user.username or self.user.user.phone_number} — {self.rate}"