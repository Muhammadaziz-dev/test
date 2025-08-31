from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification

def notify_user(recipient, verb, data=None):
    notif = Notification.objects.create(
        recipient=recipient,
        verb=verb,
        data=data or {}
    )
    payload = {
        'id':         notif.id,
        'verb':       notif.verb,
        'data':       notif.data,
        'created_at': notif.created_at.isoformat(),
        'read':       notif.read,
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_{recipient.id}",
        { "type": "notification", "payload": payload }
    )
    return notif
