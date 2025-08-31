from rest_framework import serializers
from auditlog.models import LogEntry

class LogEntrySerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    content_type = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = LogEntry
        fields = [
            'id',
            'timestamp',
            'actor_username',
            'content_type',
            'object_pk',
            'object_repr',
            'action',
            'changes',
        ]
        read_only_fields = fields
