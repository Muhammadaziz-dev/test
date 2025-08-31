from rest_framework import viewsets, permissions, status

from platform_user.models import PlatformUser
from staffs.permissions import StoreStaffPermission
from store.models import Store
from store.serializers import (
    StoreListSerializer,
    StoreDetailSerializer,
    StoreCreateUpdateSerializer
)
from rest_framework.decorators import action
from rest_framework.response import Response


class StoreViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]

    def get_queryset(self):
        user = self.request.user

        if hasattr(user, 'platform_profile'):
            platform_user = user.platform_profile

            if platform_user.chief is None:
                return Store.objects.filter(owner=platform_user)

            return Store.objects.filter(
                staff_members__user=platform_user,
                staff_members__is_active=True
            ).distinct()

        return Store.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        try:
            platform_user = user.platform_profile
        except PlatformUser.DoesNotExist:
            platform_user = PlatformUser.objects.create(user=user)

        serializer.save(owner=platform_user)

    @action(detail=True, methods=['get'], url_path='access')
    def check_access(self, request, pk=None):
        user = request.user

        if not hasattr(user, 'platform_profile'):
            return Response({"has_access": False}, status=status.HTTP_403_FORBIDDEN)

        platform_user = user.platform_profile

        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"detail": "Store not found"}, status=status.HTTP_404_NOT_FOUND)

        if store.owner == platform_user:
            return Response({"has_access": True, "role": "admin"})

        staff = store.staff_members.filter(user=platform_user, is_active=True).first()
        if staff:
            return Response({"has_access": True, "role": staff.role})

        return Response({"has_access": False}, status=status.HTTP_403_FORBIDDEN)

    def get_serializer_class(self):
        match self.action:
            case 'list':
                return StoreListSerializer
            case 'retrieve':
                return StoreDetailSerializer
            case 'create' | 'update' | 'partial_update':
                return StoreCreateUpdateSerializer
            case _:
                return StoreDetailSerializer
