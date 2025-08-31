from rest_framework import viewsets
from django_filters import rest_framework as filters
from auditlog.models import LogEntry
from .serializers import LogEntrySerializer

class LogEntryFilter(filters.FilterSet):
    action = filters.CharFilter(field_name='action')
    content_type = filters.CharFilter(field_name='content_type__model')
    actor = filters.CharFilter(field_name='actor__username')
    date_after = filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    date_before = filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')

    class Meta:
        model = LogEntry
        fields = ['action', 'content_type', 'actor', 'date_after', 'date_before']

class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list
    """
    queryset = LogEntry.objects.select_related('actor','content_type').all()
    serializer_class = LogEntrySerializer
    filterset_class = LogEntryFilter
    search_fields = ['object_repr', 'changes', 'actor__username']
    ordering_fields = ['timestamp', 'actor__username', 'content_type__model']
    ordering = ['-timestamp']
