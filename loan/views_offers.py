# loan/views_offers.py
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from store.models import Store  # adjust if different
from notifications.utils import notify_user
from .models import DebtImportOffer
from .serializers import (
    DebtImportOfferCreateSerializer,
    DebtImportOfferSerializer,
    DebtImportOfferAcceptSerializer,
    DebtImportOfferRejectSerializer,
)

# Replace with your real permission check
def user_has_store_access(user, store_id: int) -> bool:
    # Example placeholder: owner of store or staff membership, etc.
    # Return True if user is allowed to write into this store.
    return True

class DebtImportOfferViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
      POST   /platform/debt/offers/                  (create an offer; typically admin or system)
      GET    /platform/debt/offers/?status=pending   (list my offers)
      POST   /platform/debt/offers/{id}/accept/      (accept and choose store)
      POST   /platform/debt/offers/{id}/reject/      (reject)
    """
    queryset = DebtImportOffer.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return DebtImportOfferCreateSerializer
        return DebtImportOfferSerializer

    def get_queryset(self):
        # Debtor sees their own offers; you can widen for admins if needed
        qs = DebtImportOffer.objects.filter(debtor_user=self.request.user)
        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        return qs

    def perform_create(self, serializer):
        # Creator can be system/user — up to you
        offer = serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        if offer.debtor_user_id != request.user.id:
            return Response({"detail": "Not your offer."}, status=status.HTTP_403_FORBIDDEN)
        if not offer.is_pending():
            # idempotent success if already applied
            if offer.status == DebtImportOffer.Status.APPLIED and offer.applied_document_id:
                return Response(
                    {"status": "applied", "document_id": offer.applied_document_id},
                    status=status.HTTP_200_OK,
                )
            return Response({"detail": f"Offer is {offer.status}."}, status=status.HTTP_409_CONFLICT)

        s = DebtImportOfferAcceptSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        store_id = s.validated_data["store_id"]

        if not user_has_store_access(request.user, store_id):
            return Response({"detail": "No permission for this store."}, status=status.HTTP_403_FORBIDDEN)

        store = get_object_or_404(Store, pk=store_id)

        with transaction.atomic():
            # Mark as accepted first (for audit), then apply
            offer.mark(DebtImportOffer.Status.ACCEPTED, by=request.user)
            doc = offer.apply_to_store(store, actor=request.user)

        def _notify():
            # Confirmation to acceptor
            notify_user(
                request.user,
                verb=f"Debt import applied to store #{store.id}",
                data={"offer_id": offer.id, "document_id": doc.id}
            )
            # Optional: notify store admins or the creator
            if offer.created_by and offer.created_by_id != request.user.id:
                notify_user(
                    offer.created_by,
                    verb=f"Debt import accepted by {request.user}",
                    data={"offer_id": offer.id, "store_id": store.id, "document_id": doc.id}
                )
        transaction.on_commit(_notify)

        return Response({"status": "applied", "document_id": doc.id}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        offer = self.get_object()
        if offer.debtor_user_id != request.user.id:
            return Response({"detail": "Not your offer."}, status=status.HTTP_403_FORBIDDEN)
        if not offer.is_pending():
            return Response({"detail": f"Offer is {offer.status}."}, status=status.HTTP_409_CONFLICT)

        s = DebtImportOfferRejectSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        offer.mark(DebtImportOffer.Status.REJECTED, by=request.user)

        def _notify():
            if offer.created_by:
                notify_user(
                    offer.created_by,
                    verb=f"Debt import rejected by {request.user}",
                    data={"offer_id": offer.id, "reason": s.validated_data.get("reason", "")}
                )
        transaction.on_commit(_notify)

        return Response({"status": "rejected"}, status=status.HTTP_200_OK)
