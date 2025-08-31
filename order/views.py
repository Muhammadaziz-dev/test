from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from order.models import Order, ProductOrder
from order.serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    ProductOrderSerializer
)
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers

from staffs.mixins import StoreIDMixin
from staffs.permissions import StoreStaffPermission


class OrderViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['phone_number', 'first_name', 'last_name']
    filterset_fields = ['payment_type', 'currency', 'is_deleted']

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        if not store_id:
            return Order.objects.none()
        return Order.objects.active().filter(store_id=store_id)

    def get_serializer_class(self):
        match self.action:
            case 'list':
                return OrderListSerializer
            case 'retrieve':
                return OrderDetailSerializer
            case 'create':
                return OrderCreateSerializer
            case _:
                return OrderDetailSerializer

    def perform_create(self, serializer):
        store_id = self.kwargs.get('store_id')
        if not store_id:
            raise serializers.ValidationError("Shop ID is required in URL.")
        serializer.save(store_id=store_id)

    @action(detail=True, methods=['get'], url_path='items')
    def get_order_items(self, request, store_id=None, pk=None):
        order = self.get_object()
        items = order.items.all()
        serializer = ProductOrderSerializer(items, many=True)
        return Response(serializer.data)


class OrderItemsViewSet(StoreIDMixin, viewsets.ModelViewSet):
    queryset = ProductOrder.objects.select_related('order')
    serializer_class = ProductOrderSerializer
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]


class OrderTrashViewSet(StoreIDMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    lookup_field = 'pk'

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        return Order.all_objects.filter(store_id=store_id, is_deleted=True)

    def get_serializer_class(self):
        match self.action:
            case 'list':
                return OrderListSerializer
            case 'retrieve':
                return OrderDetailSerializer
            case _:
                return OrderDetailSerializer

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, store_id=None, pk=None):
        order = self.get_queryset().filter(pk=pk).first()
        if not order:
            return Response({"detail": "Order not found or not deleted."}, status=status.HTTP_404_NOT_FOUND)

        order.restore()
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete')
    def hard_delete(self, request, store_id=None, pk=None):
        order = self.get_queryset().filter(pk=pk).first()
        if not order:
            return Response({"detail": "Order not found or not deleted."}, status=status.HTTP_404_NOT_FOUND)

        order.hard_delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
