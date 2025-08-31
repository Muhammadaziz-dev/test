from rest_framework import serializers

from staffs.models import StoreStaff
from store.models import Store


class StoreListSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = ['id', 'name', 'phone_number', 'address', 'logo', 'role']

    def get_role(self, store):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'platform_profile'):
            return None

        platform_user = request.user.platform_profile

        if store.owner == platform_user:
            return 'admin'

        try:
            staff = StoreStaff.objects.get(store=store, user=platform_user, is_active=True)
            return staff.role
        except StoreStaff.DoesNotExist:
            return None


class StoreDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'owner']


class StoreCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'name', 'phone_number', 'address', 'description',
            'latitude', 'longitude', 'logo', 'banner', 'id', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', ]
