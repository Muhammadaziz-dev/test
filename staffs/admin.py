from django.contrib import admin
from .models import StoreStaff


@admin.register(StoreStaff)
class StoreStaffAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'store_display', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'store')
    search_fields = ('user__user__first_name', 'user__user__last_name', 'user__user__phone_number')
    list_per_page = 50
    ordering = ['-created_at']

    def user_display(self, obj):
        return obj.user.user.get_full_name() or obj.user.user.username or obj.user.user.phone_number
    user_display.short_description = "Xodim"

    def store_display(self, obj):
        return obj.store.name
    store_display.short_description = "Do‘kon"