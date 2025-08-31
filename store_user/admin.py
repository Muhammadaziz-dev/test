from django.contrib import admin
from .models import StoreUser


@admin.register(StoreUser)
class StoreUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'phone_number', 'address', 'is_active', 'created_at')
        }),
    )
