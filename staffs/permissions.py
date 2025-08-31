from rest_framework.permissions import BasePermission
from staffs.models import StoreStaff

from .role_permissions import ROLE_PERMISSIONS, ACTION_MAP


class StoreStaffPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        store_id = view.kwargs.get('store_id')
        action = ACTION_MAP.get(view.action)
        platform_user = getattr(user, 'platform_profile', None)

        if platform_user is None:
            return False

        # Agar chief bo‘lsa, barcha ruxsatga ega
        if platform_user.chief is None:
            return True

        model_name = self._get_model_name(view)

        if not store_id and model_name == 'store':
            # ✅ FIX: get() o‘rniga filter().exists() bilan xavfsiz tekshiruv
            return self._check_store_action_without_store_id(platform_user, action)

        if not store_id:
            return False

        try:
            # ✅ FIX: get() xavfsiz, chunki bu yerda store_id bor (aniq do‘kon)
            staff = StoreStaff.objects.get(user=platform_user, store_id=store_id, is_active=True)
        except StoreStaff.DoesNotExist:
            return False

        allowed_actions = ROLE_PERMISSIONS.get(staff.role, {}).get(model_name, [])
        return action in allowed_actions

    def has_object_permission(self, request, view, obj):
        return True

    def _get_model_name(self, view):
        if hasattr(view, 'queryset') and view.queryset is not None:
            return view.queryset.model._meta.model_name.lower()
        if hasattr(view, 'get_queryset'):
            queryset = view.get_queryset()
            if hasattr(queryset, 'model'):
                return queryset.model._meta.model_name.lower()
        return ''

    def _check_store_action_without_store_id(self, platform_user, action):
        # ✅ FIX: .get() o‘rniga filter().exists() ishlatilmoqda
        staff_qs = StoreStaff.objects.filter(user=platform_user, is_active=True)

        if not staff_qs.exists():
            return False

        # ✅ FIX: create/update uchun 'manager' roli bo‘lishi shart
        if action in ['create', 'update']:
            return staff_qs.filter(role='manager').exists()

        # Aks holda faqat mavjudligi kifoya
        return True
