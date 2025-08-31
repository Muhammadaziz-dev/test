from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from config.pagination import StandardResultsSetPagination
from staffs.permissions import StoreStaffPermission
from rest_framework.exceptions import PermissionDenied, NotFound
from .models import Cashbox, CashTransaction
from .serializers import CashboxSerializer, CashTransactionSerializer
from staffs.models import StoreStaff
from django.core.exceptions import ObjectDoesNotExist
from store.models import Store


class CashboxDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        user = request.user

        try:
            cashbox = Cashbox.objects.select_related('store').get(store_id=store_id)
        except Cashbox.DoesNotExist:
            raise NotFound("Ushbu do‘kon uchun kassa mavjud emas.")

        if cashbox.store.owner == user.platform_profile:
            serializer = CashboxSerializer(cashbox)
            return Response(serializer.data)

        if not hasattr(user, 'platform_profile'):
            raise PermissionDenied("Siz bu kassani ko‘rish huquqiga ega emassiz.")

        platform_user = user.platform_profile

        is_staff = StoreStaff.objects.filter(
            user=platform_user, store_id=store_id, is_active=True
        ).exists()

        if not is_staff:
            raise PermissionDenied("Siz bu kassani ko‘rish huquqiga ega emassiz.")

        serializer = CashboxSerializer(cashbox)
        return Response(serializer.data)


class CashTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        user = request.user

        if not hasattr(user, 'platform_profile'):
            try:
                if Store.objects.filter(id=store_id, owner=user).exists():
                    return self.paginated_response(store_id, request)
            except ObjectDoesNotExist:
                raise PermissionDenied("Do‘kon topilmadi.")

        if not hasattr(user, 'platform_profile'):
            raise PermissionDenied("Siz bu amaliyotni bajarishga ruxsat yo‘q.")

        platform_user = user.platform_profile
        allowed_roles = ["manager", "cashier", ]

        if platform_user.chief :
            try:
                staff = StoreStaff.objects.get(user=platform_user, store_id=store_id, is_active=True)
                if staff.role not in allowed_roles:
                    raise PermissionDenied("Sizga bu amaliyotni bajarishga ruxsat yo‘q.")
            except StoreStaff.DoesNotExist:
                raise PermissionDenied("Siz ushbu do‘konda xodim emassiz.")

        return self.paginated_response(store_id, request)

    def get_transactions(self, store_id):
        return CashTransaction.objects.select_related(
            'cashbox', 'order', 'cashbox__store'
        ).filter(cashbox__store_id=store_id)

    def paginated_response(self, store_id, request):
        transactions = self.get_transactions(store_id)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(transactions, request)
        serializer = CashTransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
