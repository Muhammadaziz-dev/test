# your_project/audit_admin.py

from django.contrib import admin
from auditlog.models import LogEntry

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = (
      'action_time', 'actor', 'content_type', 'object_repr',
      'action', 'changes'
    )
    list_filter = ('action', 'content_type')
    search_fields = ('actor__username','object_repr','changes')
    readonly_fields = (
      'actor','action_time','content_type','object_repr',
      'action','changes','object_pk',
    )
