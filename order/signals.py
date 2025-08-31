# order/signals.py
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_currentuser.middleware import get_current_authenticated_user
from decimal import Decimal
from order.models import Order
from notifications.utils import notify_user

@receiver(post_save, sender=Order)
def send_order_notification(sender, instance: Order, created, **kwargs):
    # only trigger on the *first* save of a new Order
    if not created:
        return

    # who placed it?
    actor = get_current_authenticated_user()
    if not actor or actor.is_anonymous:
        return

    # register the notify_user call to fire after the DB transaction commits
    def _send():
        notify_user(
            recipient=actor,
            verb=f"You placed Order #{instance.pk}",
            data={
                "order_id":    instance.pk,
                "total_price": str(instance.total_price or Decimal('0.00')),
                "created_at":  instance.created_at.isoformat(),
            }
        )
    transaction.on_commit(_send)
