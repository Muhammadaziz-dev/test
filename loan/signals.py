# loan/signals.py
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import DebtDocument, DebtUser, DebtImportOffer
from notifications.utils import notify_user

User = get_user_model()


def _resolve_debtuser_platform_user(du: DebtUser) -> User | None:
    """
    1) Prefer explicit FK: DebtUser.user (if you have it)
    2) Fallback to CustomUser by phone_number
    """
    user = getattr(du, "user", None)
    if user:
        return user
    try:
        return User.objects.get(phone_number=du.phone_number)
    except User.DoesNotExist:
        return None


def _debt_payload(doc: DebtDocument) -> dict:
    return {
        "debtuser": str(doc.debtuser) if doc.debtuser else None,
        "method": doc.method,  # "transfer" | "accept"
        "currency": doc.currency,
        "cash_amount": str(doc.cash_amount or Decimal("0")),
        "product_amount": str(doc.product_amount or Decimal("0")),
        "total_amount": str(doc.total_amount or Decimal("0")),
        "date": doc.date.isoformat(),
    }


@receiver(post_save, sender=DebtDocument)
def notify_on_debt_document_create(sender, instance: DebtDocument, created, **kwargs):
    # Only on create, skip mirror copies
    if not created or instance.is_mirror:
        return

    payload = _debt_payload(instance)
    owner = instance.owner  # might be None when created from Admin if you didn't set it
    debtor_user = _resolve_debtuser_platform_user(instance.debtuser) if instance.debtuser_id else None

    def _send():
        # 1) Notify the actor/owner if present
        if owner:
            if instance.method == "transfer":
                verb_owner = f"Debt recorded for {instance.debtuser}"
            else:
                verb_owner = f"Payment accepted from {instance.debtuser}"
            notify_user(owner, verb_owner, data=payload)

        # 2) Notify the debtor
        if debtor_user:
            if instance.method == "transfer":
                verb_debtor = f"Debt added from {owner}" if owner else "Debt recorded on your account"
            else:
                verb_debtor = "Your payment was recorded"
            notify_user(debtor_user, verb_debtor, data=payload)

    # ensure total_amount/product_amount are persisted and any transactions are committed
    transaction.on_commit(_send)


@receiver(post_save, sender=DebtImportOffer)
def notify_on_offer_create(sender, instance: DebtImportOffer, created, **kwargs):
    if not created:
        return
    def _send():
        notify_user(
            instance.debtor_user,
            verb="Dept import pending",
            data={
                "offer_id": instance.id,
                "amount": str(instance.payload.get("amount")),
                "currency": instance.payload.get("currency", "USD"),
                "creditor": instance.payload.get("creditor_name"),
                "action": "review_import"
            }
        )
    transaction.on_commit(_send())
