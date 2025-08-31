from django.db import models
from platform_user.models import PlatformUser
from store.models import Store

STAFF_ROLE_CHOICES = [
    ('manager', 'Manager'),
    ('seller', 'Seller'),
    ('deliverer', 'Yetkazuvchi'),
    ('cashier', 'Kassir'),
    ('stockman', 'Omborchi'),
    ('viewer', 'Faqat ko‘rish huquqi'),
]


class StoreStaff(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="staff_members")
    user = models.ForeignKey(PlatformUser, on_delete=models.CASCADE, related_name="store_roles")
    role = models.CharField(max_length=20, choices=STAFF_ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('store', 'user')
        verbose_name = "Do‘kon xodimi"
        verbose_name_plural = "Do‘kon xodimlari"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.store.name} ({self.get_role_display()})"
