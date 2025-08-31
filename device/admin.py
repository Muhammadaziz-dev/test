from django.contrib import admin
from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        'user_display',
        'device_type',
        'os',
        'browser',
        'ip_address',
        'where',
        'is_active',
        'last_login',
        'created_at',
    )
    list_filter = ('is_active', 'where', 'device_type', 'os', 'browser')
    search_fields = ('user__username', 'user__phone_number', 'ip_address', 'brand', 'model')
    readonly_fields = ('last_login', 'created_at')

    def user_display(self, obj):
        return f"{obj.user.get_full_name()} ({obj.user.phone_number})"
    user_display.short_description = "Foydalanuvchi"