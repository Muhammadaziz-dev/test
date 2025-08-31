from staffs.mixins import StoreIDMixin
from staffs.permissions import StoreStaffPermission
from .models import StockTransfer, ProductSale, ProductEntrySystem
from .serializers import (
    StockTransferSerializer,
    ProductSaleSerializer, ProductEntrySystemReadSerializer, ProductEntrySystemWriteSerializer,
)
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response


class StockTransferViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    http_method_names = ['get', 'post', 'delete']
    serializer_class = StockTransferSerializer

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        if not store_id:
            return StockTransfer.objects.none()
        return StockTransfer.objects.filter(product__store_id=store_id)

    def perform_create(self, serializer):
        product = serializer.validated_data.get('product')
        store_id = self.kwargs.get('store_id')

        if not store_id:
            raise serializers.ValidationError("Store ID not provided in URL.")

        if product.store_id != int(store_id):
            raise serializers.ValidationError("Mahsulot ushbu do'konga tegishli emas.")

        serializer.save(auto=False)


class ProductSaleViewSet(StoreIDMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    serializer_class = ProductSaleSerializer

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        if not store_id:
            return ProductSale.objects.none()
        return ProductSale.objects.filter(product__store_id=store_id)


class ProductEntrySystemViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]

    def get_queryset(self):
        store_id = self.get_store_id()
        return (ProductEntrySystem.objects
                .filter(store_id=store_id)
                .select_related('product', 'store'))

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['store'] = self.get_store()
        return ctx

    def get_serializer_class(self):

        if self.action in ('list', 'retrieve'):
            return ProductEntrySystemReadSerializer
        return ProductEntrySystemWriteSerializer

    def perform_create(self, serializer):
        serializer.save(store=self.get_store())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance
        read_ser = ProductEntrySystemReadSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(read_ser.data)
        return Response(read_ser.data, status=status.HTTP_201_CREATED, headers=headers)