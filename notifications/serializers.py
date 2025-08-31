from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['id', 'verb', 'data', 'created_at', 'read']
        read_only_fields = ['id','created_at']
