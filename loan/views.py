from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from notifications.utils import notify_user
from .models import DebtUser, DebtDocument, DocumentProduct
from .serializers import (
    DebtUserSerializer,
    DebtDocumentSerializer,
    DocumentProductSerializer,
    DebtUserMessageSerializer,
)

User = get_user_model()


# ----------------------------------------------------------------------
# Helpers for resolving users and building payloads
# ----------------------------------------------------------------------
def _resolve_debtuser_platform_user(du: DebtUser) -> User | None:
    """
    1) Prefer an explicit FK (DebtUser.user).
    2) Fallback to CustomUser by phone_number.
    """
    user = getattr(du, "user", None)
    if user:
        return user
    try:
        return User.objects.get(phone_number=du.phone_number)
    except User.DoesNotExist:
        return None


def _debt_payload(doc: DebtDocument) -> dict:
    """Build a compact JSON-serializable representation of a debt document."""
    return {
        "debtuser": str(doc.debtuser) if doc.debtuser else None,
        "method": doc.method,
        "currency": doc.currency,
        "cash_amount": str(doc.cash_amount or Decimal("0")),
        "product_amount": str(doc.product_amount or Decimal("0")),
        "total_amount": str(doc.total_amount or Decimal("0")),
        "date": doc.date.isoformat(),
    }


# ----------------------------------------------------------------------
# Mixin to scope all actions by the store_id from the URL
# ----------------------------------------------------------------------
class StoreScopedMixin:
    permission_classes = [IsAuthenticated]

    def get_store_id(self) -> int:
        return int(self.kwargs.get("store_id"))

    def ensure_same_store(self, obj_store_id: int):
        if obj_store_id != self.get_store_id():
            raise NotFound("Object not found in this store.")


# ----------------------------------------------------------------------
# ViewSets
# ----------------------------------------------------------------------
class DebtUserViewSet(StoreScopedMixin, viewsets.ModelViewSet):
    """
    /platform/<store_id>/debt/debtors/
    """
    serializer_class = DebtUserSerializer

    def get_queryset(self):
        return DebtUser.objects.filter(store_id=self.get_store_id(), is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(store_id=self.get_store_id())

    @action(detail=True, methods=["post"])
    def soft_delete(self, request, store_id=None, pk=None):
        obj = self.get_object()
        self.ensure_same_store(obj.store_id)
        obj.delete()
        return Response({"status": "deleted"}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def restore(self, request, store_id=None, pk=None):
        obj = self.get_object()
        self.ensure_same_store(obj.store_id)
        if hasattr(obj, "restore"):
            obj.restore()
        return Response({"status": "restored"}, status=status.HTTP_200_OK)


class DebtDocumentViewSet(StoreScopedMixin, viewsets.ModelViewSet):
    """
    /platform/<store_id>/debt/debtors/{debtor_pk}/documents/
    """
    serializer_class = DebtDocumentSerializer

    def get_store_id(self) -> int:
        return int(self.kwargs.get("store_id"))

    def get_debtor_id(self) -> int | None:
        v = self.kwargs.get("debtor_pk")
        return int(v) if v is not None else None

    def get_queryset(self):
        qs = DebtDocument.objects.filter(store_id=self.get_store_id())
        debtor_pk = self.get_debtor_id()
        if debtor_pk:
            qs = qs.filter(debtuser_id=debtor_pk)
        show = self.request.query_params.get("show")
        if show == "deleted":
            return qs.filter(is_deleted=True)
        if show == "all":
            return qs
        return qs.filter(is_deleted=False)

    def perform_create(self, serializer):
        """
        Ensure store_id and owner are set, and send notifications after commit.
        """
        store_id = self.get_store_id()
        debtor_id = self.get_debtor_id()
        owner = self.request.user

        # Persist the document; set owner if not explicitly provided
        save_kwargs = {"store_id": store_id, "owner": owner}
        if debtor_id:
            save_kwargs["debtuser_id"] = debtor_id
        document: DebtDocument = serializer.save(**save_kwargs)

        # Immediately recompute debtor balance if this isn’t a mirror
        if not document.is_mirror and document.debtuser:
            document.debtuser.recalculate_balance()

        # Schedule notifications after the transaction commits
        def _send_notifications():
            debtor_user = _resolve_debtuser_platform_user(document.debtuser)
            payload = _debt_payload(document)

            # Notify the actor (owner)
            if document.method == "transfer":
                verb_owner = f"Debt recorded for {document.debtuser}"
            else:
                verb_owner = f"Payment accepted from {document.debtuser}"
            notify_user(owner, verb_owner, data=payload)

            # Notify the debtor (platform user) if different
            if debtor_user and debtor_user.id != owner.id:
                if document.method == "transfer":
                    verb_debtor = (
                        f"Debt added from {owner}"
                        if owner
                        else "Debt recorded on your account"
                    )
                else:
                    verb_debtor = "Your payment was recorded"
                notify_user(debtor_user, verb_debtor, data=payload)

        transaction.on_commit(_send_notifications)

    def perform_update(self, serializer):
        inst = self.get_object()
        self.ensure_same_store(inst.store_id)
        if self.get_debtor_id() and inst.debtuser_id != self.get_debtor_id():
            raise PermissionDenied("Cannot move document to another debtor.")
        doc: DebtDocument = serializer.save()
        if not doc.is_mirror and doc.debtuser:
            doc.debtuser.recalculate_balance()

    def destroy(self, request, *args, **kwargs):
        doc = self.get_object()
        doc.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="trash")
    def trash(self, request, store_id=None, debtor_pk=None):
        qs = DebtDocument.objects.filter(
            store_id=self.get_store_id(),
            debtuser_id=self.get_debtor_id(),
            is_deleted=True,
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def restore(self, request, store_id=None, debtor_pk=None, pk=None):
        doc = DebtDocument.objects.filter(
            pk=pk,
            store_id=self.get_store_id(),
            debtuser_id=self.get_debtor_id(),
        ).first()
        if not doc:
            raise NotFound("Document not found.")
        doc.restore()
        return Response({"status": "restored"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="trash/restore")
    def trash_restore(self, request, store_id=None, debtor_pk=None):
        ids = request.data.get("ids", [])
        qs = DebtDocument.objects.filter(
            store_id=self.get_store_id(),
            debtuser_id=self.get_debtor_id(),
            id__in=ids,
            is_deleted=True,
        )
        cnt = 0
        for d in qs:
            d.restore()
            cnt += 1
        return Response({"restored": cnt}, status=status.HTTP_200_OK)


class DocumentProductViewSet(StoreScopedMixin, viewsets.ModelViewSet):
    """
    /platform/<store_id>/debt/debtors/{debtor_pk}/documents/{document_pk}/products/
    """
    serializer_class = DocumentProductSerializer

    def get_queryset(self):
        qs = (
            DocumentProduct.objects.select_related("document", "product")
            .filter(document__store_id=self.get_store_id())
        )
        debtor_pk = self.kwargs.get("debtor_pk")
        document_pk = self.kwargs.get("document_pk")
        if debtor_pk:
            qs = qs.filter(document__debtuser_id=debtor_pk)
        if document_pk:
            qs = qs.filter(document_id=document_pk)
        return qs

    # --- Helper to recompute totals and debtor balance ---
    def _recompute_document_totals(self, doc: DebtDocument):
        total_products = doc.products.aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        new_total = (doc.cash_amount or Decimal("0.00")) + total_products
        DebtDocument.objects.filter(pk=doc.pk).update(
            product_amount=total_products, total_amount=new_total
        )
        if doc.debtuser_id and not doc.is_mirror and not doc.is_deleted:
            doc.debtuser.recalculate_balance()

    def perform_create(self, serializer):
        doc = get_object_or_404(
            DebtDocument.objects.select_related("debtuser"),
            pk=self.kwargs.get("document_pk"),
        )
        self.ensure_same_store(doc.store_id)
        if self.kwargs.get("debtor_pk") and doc.debtuser_id != int(self.kwargs["debtor_pk"]):
            raise PermissionDenied("Document does not belong to this debtor.")
        obj = serializer.save(document=doc)
        self._recompute_document_totals(doc)
        return obj

    def perform_update(self, serializer):
        instance = self.get_object()
        self.ensure_same_store(instance.document.store_id)
        obj = serializer.save()
        self._recompute_document_totals(instance.document)
        return obj

    def perform_destroy(self, instance):
        doc = instance.document
        self.ensure_same_store(doc.store_id)
        super().perform_destroy(instance)
        self._recompute_document_totals(doc)


# ----------------------------------------------------------------------
# Manual message API
# ----------------------------------------------------------------------
class DebtUserMessageView(StoreScopedMixin, APIView):
    """
    POST /platform/<store_id>/debt/debtors/send-message/
    {
      "phone_number": "+998901234567",
      "title":        "Payment Reminder",
      "description":  "Your debt of 100 USD is due tomorrow.",
      "action":       "copy"
    }
    Sends an in-app notification to the debtor’s platform user.
    """

    def post(self, request, store_id=None):
        serializer = DebtUserMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]
        title = serializer.validated_data["title"]
        description = serializer.validated_data["description"]
        action = serializer.validated_data["action"]

        du = DebtUser.objects.filter(
            store_id=self.get_store_id(),
            phone_number=phone,
            is_deleted=False,
        ).first()
        if du is None:
            return Response(
                {"detail": "DebtUser not found in this store."},
                status=status.HTTP_404_NOT_FOUND,
            )

        recipient = _resolve_debtuser_platform_user(du)
        if recipient is None:
            return Response(
                {"detail": "No platform user with that phone number."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notify_user(
            recipient,
            verb=title,
            data={"description": description, "action": action},
        )
        return Response({"status": "message sent"}, status=status.HTTP_201_CREATED)
