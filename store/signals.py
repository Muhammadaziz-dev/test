from django.db.models.signals import post_save
from django.dispatch import receiver
from cashbox.models import Cashbox
from .models import Store

@receiver(post_save, sender=Store)
def create_store_cashbox(sender, instance, created, **kwargs):
    if created:
        Cashbox.objects.get_or_create(store=instance)
