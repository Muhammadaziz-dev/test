from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


from .models import Notification
from .serializers import NotificationSerializer

class NotificationFilter(filters.FilterSet):
    read = filters.BooleanFilter(field_name='read')
    class Meta:
        model  = Notification
        fields = ['read']

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_class    = NotificationFilter
    ordering_fields    = ['created_at']
    ordering           = ['-created_at']

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def perform_create(self, serializer):
        notification = serializer.save(recipient=self.request.user)
        channel_layer = get_channel_layer
        group_name = f"notifications_{notification.recipient.id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification",
                "payload": NotificationSerializer(notification).data
            }
        )


    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({"status":"marked as read"})
