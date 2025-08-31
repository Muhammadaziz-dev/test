from platform_user.models import PlatformUser, RateUsd
from platform_user.serializers import (
    PlatformUserCreateUpdateSerializer,
    PlatformUserListSerializer,
    PlatformUserDetailSerializer, RateUsdSerializer
)
from rest_framework.decorators import action
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from staffs.mixins import StoreIDMixin
from staffs.permissions import StoreStaffPermission


class PlatformUserViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['user__first_name', 'user__last_name', 'user__phone_number', 'user__email', 'user__username']
    filterset_fields = ['chief']

    queryset = PlatformUser.objects.select_related('user')

    def get_queryset(self):
        return PlatformUser.objects.select_related('user').order_by('-id')

    def get_serializer_class(self):
        match self.action:
            case 'list':
                return PlatformUserListSerializer
            case 'retrieve':
                return PlatformUserDetailSerializer
            case 'create':
                return PlatformUserCreateUpdateSerializer
            case 'update' | 'partial_update':
                return PlatformUserCreateUpdateSerializer
            case _:
                return PlatformUserDetailSerializer

    def perform_create(self, serializer):
        serializer.save(chief=self.request.user.platform_profile)

    def perform_update(self, serializer):
        serializer.save(chief=self.request.user.platform_profile)


class RateUsdViewSet(viewsets.ModelViewSet):
    serializer_class = RateUsdSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_target_user(self):
        platform_user = self.request.user.platform_profile
        return platform_user.chief if platform_user.chief else platform_user

    def get_queryset(self):
        return RateUsd.objects.filter(user=self.get_target_user())

    def perform_create(self, serializer):
        serializer.save(user=self.get_target_user())

    def create(self, request, *args, **kwargs):
        if RateUsd.objects.filter(user=self.get_target_user()).exists():
            return Response({"detail": "Rate record already exists."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = RateUsd.objects.get(user=self.get_target_user())
        except RateUsd.DoesNotExist:
            return Response({"detail": "RateUsd not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my')
    def my_rate(self, request):
        try:
            instance = RateUsd.objects.get(user=self.get_target_user())
        except RateUsd.DoesNotExist:
            return Response({"detail": "RateUsd not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
