from accounts.models import CustomUser
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PlatformUser, RateUsd

class PlatformUserListSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='user.phone_number')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    profile_image = serializers.ImageField(source='user.profile_image')

    class Meta:
        model = PlatformUser
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'profile_image', 'is_verified', 'created_at']


class PlatformUserDetailSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='user.phone_number')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    username = serializers.CharField(source='user.username')
    gender = serializers.CharField(source='user.gender')
    profile_image = serializers.ImageField(source='user.profile_image')

    class Meta:
        model = PlatformUser
        fields = [
            'id', 'phone_number', 'first_name', 'last_name',
            'email', 'username', 'gender', 'profile_image',
            'is_verified', 'chief', 'created_at'
        ]


class RateUsdSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(read_only=True, source='user')

    class Meta:
        model = RateUsd
        fields = ['user_id', 'rate', 'date']
        read_only_fields = ['user_id', 'date']

class PlatformUserCreateUpdateSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='user.phone_number')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email', required=False, allow_blank=True)
    username = serializers.CharField(source='user.username', required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False)
    gender = serializers.ChoiceField(choices=CustomUser.Gender, source='user.gender', required=False)
    profile_image = serializers.ImageField(source='user.profile_image', required=False, allow_null=True)

    class Meta:
        model = PlatformUser
        fields = [
            'phone_number', 'first_name', 'last_name', 'email', 'username', 'password',
            'gender', 'profile_image', 'is_verified', 'chief'
        ]

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        phone_number = user_data.pop('phone_number')

        user, created = CustomUser.objects.update_or_create(
            phone_number=phone_number,
            defaults=user_data
        )

        password = self.initial_data.get("password")
        if password:
            user.set_password(password)
            user.save()

        platform_user, _ = PlatformUser.objects.get_or_create(
            user=user,
            defaults={
                'is_verified': validated_data.get('is_verified', False),
                'chief': self.context['request'].user.platform_profile
            }
        )
        return platform_user

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        for field, value in user_data.items():
            if field == "password":
                user.set_password(value)
            else:
                setattr(user, field, value)
        user.save()

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        return instance