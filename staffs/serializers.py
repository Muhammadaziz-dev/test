from rest_framework import serializers
from .models import StoreStaff
from platform_user.serializers import PlatformUserListSerializer
from platform_user.models import PlatformUser


class StoreStaffSerializer(serializers.ModelSerializer):
    user_detail = PlatformUserListSerializer(source='user', read_only=True)
    user = serializers.PrimaryKeyRelatedField(queryset=PlatformUser.objects.all())
    store = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StoreStaff
        fields = ['id', 'store', 'user', 'user_detail', 'role', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at', 'user_detail', 'store']
