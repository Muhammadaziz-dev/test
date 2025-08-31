# staffs/views.py
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .mixins import StoreIDMixin
from .models import StoreStaff
from .permissions import StoreStaffPermission
from .serializers import StoreStaffSerializer
from django.shortcuts import get_object_or_404
from store.models import Store

class StoreStaffViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    serializer_class = StoreStaffSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['user__user__first_name', 'user__user__phone_number']
    filterset_fields = ['role', 'is_active']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        return StoreStaff.objects.filter(store_id=store_id).select_related('user__user', 'store')

    def perform_create(self, serializer):
        store_id = self.kwargs.get('store_id')
        store = get_object_or_404(Store, pk=store_id)
        serializer.save(store=store)

    def perform_update(self, serializer):
        store_id = self.kwargs.get('store_id')
        store = get_object_or_404(Store, pk=store_id)
        serializer.save(store=store)
