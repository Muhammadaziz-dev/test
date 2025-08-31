from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from accounts.models import CustomUser
from device.models import Device


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "first_name", "last_name",
            "phone_number", "email", "gender", "profile_image"
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "first_name", "last_name", "username",
            "email", "gender", "profile_image"
        ]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
            "username": {"required": False, "allow_blank": True},
            "profile_image": {"required": False, "allow_null": True},
        }


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    device = serializers.DictField(required=False)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')
        device_info = data.get('device', {})

        user = authenticate(username=identifier, password=password)
        if not user or not user.is_active:
            raise serializers.ValidationError("Login ma'lumotlari noto‘g‘ri.")

        refresh = RefreshToken.for_user(user)

        Device.objects.update_or_create(
            user=user,
            device_type=device_info.get('device_type', 'unknown'),
            os=device_info.get('os', 'unknown'),
            browser=device_info.get('browser', 'unknown'),
            brand=device_info.get('brand'),
            model=device_info.get('model'),
            ip_address=device_info.get('ip_address'),
            where=device_info.get('where', 'platform'),
            is_active=True,
            defaults={
                'refresh_token': str(refresh)
            }
        )

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "email": user.email,
                "profile_image": user.profile_image.url if user.profile_image else None
            }
        }
