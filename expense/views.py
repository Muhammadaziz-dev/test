# expense/views.py
from rest_framework import viewsets, permissions
from staffs.mixins import StoreIDMixin
from staffs.permissions import StoreStaffPermission
from .models import Expense
from .serializers import ExpenseSerializer
from rest_framework import serializers

class ExpenseViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    serializer_class = ExpenseSerializer
    # OLD: http_method_names = ['get', 'post', 'delete']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']  # <-- CRUD

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        if not store_id:
            return Expense.objects.none()
        return Expense.objects.filter(store=store_id)

    def perform_create(self, serializer):
        store_id = self.kwargs.get('store_id')
        if not store_id:
            raise serializers.ValidationError("Shop ID not provided in URL.")
        serializer.save(store_id=store_id)

    def perform_update(self, serializer):
        """Store URL orqali qat’iy belgilanadi; body orqali o‘zgartirib bo‘lmaydi."""
        store_id = self.kwargs.get('store_id')
        if not store_id:
            raise serializers.ValidationError("Shop ID not provided in URL.")
        serializer.save(store_id=store_id)
