from .models import PlatformUser, RateUsd

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=PlatformUser)
def create_rate_usd_for_user(sender, instance, created, **kwargs):
    if created:
        RateUsd.objects.get_or_create(user=instance)