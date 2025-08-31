# devices/serializers.py
from rest_framework import serializers
from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'id', 'device_type', 'os', 'browser', 'brand', 'model',
            'ip_address', 'last_login', 'where', 'is_active'
        ]
