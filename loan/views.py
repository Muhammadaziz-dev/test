from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound

from .models import DebtUser, DebtDocument, DocumentProduct
from .serializers import DebtUserSerializer, DebtDocumentSerializer, DocumentProductSerializer

class StoreScopedMixin:
    """
    URL dan kelgan store_id bo'yicha barcha resurslarni scope qilish uchun mixin.
    """
    def get_store_id(self) -> int:
        # config.platform.py dagi '<int:store_id>/' segmentidan keladi
        return int(self.kwargs.get('store_id'))

    def ensure_same_store(self, obj_store_id: int):
        # Xavfsizlik uchun noto'g'ri store bo'lsa 404 qaytaramiz (ma'lumot sizib chiqmasin)
        if obj_store_id != self.get_store_id():
            raise NotFound()





class DebtUserViewSet(viewsets.ModelViewSet):
    serializer_class = DebtUserSerializer

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        # Default: faqat faol (o‘chirilmagan) debtorlar
        return DebtUser.objects.filter(store_id=store_id, is_deleted=False)

    def destroy(self, request, *args, **kwargs):
        """DELETE -> trash (soft delete)"""
        obj = self.get_object()
        obj.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='trash')
    def trash(self, request, store_id=None):
        """Trash ro‘yxati (o‘chirilganlar)"""
        store_id = self.kwargs.get('store_id')
        qs = DebtUser.objects.filter(store_id=store_id, is_deleted=True)
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, store_id=None, pk=None):
        """Bitta debtorni trash’dan qaytarish"""
        obj = self.get_object()  # bu trash’da ham topiladi (router detail)
        obj.restore()
        return Response({'status': 'restored'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='trash/restore')
    def trash_restore(self, request, store_id=None):
        """Bir nechta debtorni bulk tarzda qaytarish: {"ids":[1,2,3]}"""
        store_id = self.kwargs.get('store_id')
        ids = request.data.get('ids', [])
        qs = DebtUser.objects.filter(store_id=store_id, id__in=ids, is_deleted=True)
        cnt = 0
        for u in qs:
            u.restore()
            cnt += 1
        return Response({'restored': cnt}, status=status.HTTP_200_OK)


class DebtDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DebtDocumentSerializer

    def get_store_id(self) -> int:
        return int(self.kwargs.get('store_id'))

    def get_debtor_id(self) -> int | None:
        v = self.kwargs.get('debtor_pk')
        return int(v) if v is not None else None

    def get_queryset(self):
        store_id = self.get_store_id()
        debtor_id = self.get_debtor_id()
        qs = DebtDocument.objects.filter(store_id=store_id)
        if debtor_id:
            qs = qs.filter(debtuser_id=debtor_id)

        # Default: faqat o‘chirilmaganlar
        show = self.request.query_params.get('show')
        if show == 'deleted':
            return qs.filter(is_deleted=True)
        if show == 'all':
            return qs
        return qs.filter(is_deleted=False)

    def perform_create(self, serializer):
        store_id = self.get_store_id()
        debtor_id = self.get_debtor_id()
        if debtor_id:
            serializer.save(store_id=store_id, debtuser_id=debtor_id)
        else:
            serializer.save(store_id=store_id)

    def perform_update(self, serializer):
        # Debtor/store’ni URLdan tashqariga ko‘chirishga yo‘l qo‘ymaymiz
        instance = self.get_object()
        if instance.store_id != self.get_store_id():
            raise PermissionDenied("Cannot move document to another store.")
        if self.get_debtor_id() and instance.debtuser_id != self.get_debtor_id():
            raise PermissionDenied("Cannot move document to another debtor.")
        serializer.save()

    # DELETE -> soft delete (trashga yuborish)
    def destroy(self, request, *args, **kwargs):
        doc = self.get_object()
        doc.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---- TRASH (collection) ----
    @action(detail=False, methods=['get'], url_path='trash')
    def trash(self, request, store_id=None, debtor_pk=None):
        qs = DebtDocument.objects.filter(
            store_id=self.get_store_id(),
            debtuser_id=self.get_debtor_id(),
            is_deleted=True
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data, status=status.HTTP_200_OK)

    # ---- RESTORE (detail) ----
    @action(detail=True, methods=['post'])
    def restore(self, request, store_id=None, debtor_pk=None, pk=None):
        # get_object() default queryset’da is_deleted=False filtrlangan — o'chirilganni topolmaydi.
        doc = DebtDocument.objects.filter(
            pk=pk,
            store_id=self.get_store_id(),
            debtuser_id=self.get_debtor_id()
        ).first()
        if not doc:
            raise NotFound("Document not found.")
        doc.restore()
        return Response({'status': 'restored'}, status=status.HTTP_200_OK)

    # ---- BULK RESTORE (collection) ----
    @action(detail=False, methods=['post'], url_path='trash/restore')
    def trash_restore(self, request, store_id=None, debtor_pk=None):
        ids = request.data.get('ids', [])
        qs = DebtDocument.objects.filter(
            store_id=self.get_store_id(),
            debtuser_id=self.get_debtor_id(),
            id__in=ids,
            is_deleted=True
        )
        cnt = 0
        for d in qs:
            d.restore()
            cnt += 1
        return Response({'restored': cnt}, status=status.HTTP_200_OK)

class DocumentProductViewSet(StoreScopedMixin, viewsets.ModelViewSet):
    """
    /platform/<store_id>/debt/debtors/{debtor_pk}/documents/{document_pk}/products/
    """
    serializer_class = DocumentProductSerializer

    def get_queryset(self):
        qs = (DocumentProduct.objects
              .select_related('document', 'product')
              .filter(document__store_id=self.get_store_id()))
        debtor_pk = self.kwargs.get('debtor_pk')
        document_pk = self.kwargs.get('document_pk')
        if debtor_pk:
            qs = qs.filter(document__debtuser_id=debtor_pk)
        if document_pk:
            qs = qs.filter(document_id=document_pk)
        return qs

    # ---- Totallarni qayta hisoblash yordamchi ----
    def _recompute_document_totals(self, doc: DebtDocument):
        total_products = doc.products.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        new_total = (doc.cash_amount or Decimal('0.00')) + total_products
        # Yon-efektlarsiz yangilash
        DebtDocument.objects.filter(pk=doc.pk).update(
            product_amount=total_products,
            total_amount=new_total
        )
        # Debtor balansini ham yangilaymiz (mirror/soft-delete emas)
        if doc.debtuser_id and not doc.is_mirror and not doc.is_deleted:
            doc.debtuser.recalculate_balance()

    def perform_create(self, serializer):
        document_pk = self.kwargs.get('document_pk')
        doc = get_object_or_404(DebtDocument.objects.select_related('debtuser'), pk=document_pk)
        self.ensure_same_store(doc.store_id)
        if self.kwargs.get('debtor_pk') and doc.debtuser_id != int(self.kwargs['debtor_pk']):
            raise PermissionDenied("Document does not belong to this debtor.")
        obj = serializer.save(document=doc)
        # Birinchi saqlashdayoq totals yangilansin
        self._recompute_document_totals(doc)
        return obj

    def perform_update(self, serializer):
        instance = self.get_object()
        self.ensure_same_store(instance.document.store_id)
        obj = serializer.save()
        # Yangilaganda ham totals yangilansin
        self._recompute_document_totals(instance.document)
        return obj

    def perform_destroy(self, instance):
        # DRF 3.15+ da perform_destroy(self, instance) imzosi; call chain:
        # self.perform_destroy(instance) -> instance.delete()
        doc = instance.document
        self.ensure_same_store(doc.store_id)
        super().perform_destroy(instance)  # actually deletes
        # O'chirilgandan keyin totals yangilash
        self._recompute_document_totals(doc)
