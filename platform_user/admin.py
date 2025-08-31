from django.contrib import admin
from .models import PlatformUser, RateUsd


@admin.register(PlatformUser)
class PlatformUserAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'chief_display', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('user__username', 'user__phone_number')

    def user_display(self, obj):
        return f"{obj.user.username or obj.user.phone_number}"
    user_display.short_description = "Foydalanuvchi"

    def chief_display(self, obj):
        if obj.chief:
            return f"{obj.chief.user.username or obj.chief.user.phone_number}"
        return "-"
    chief_display.short_description = "Rahbari"


@admin.register(RateUsd)
class RateUsdAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'rate', 'date')
    search_fields = ('user__username', 'user__phone_number')

    def user_display(self, obj):
        return f"{obj.user.user.username or obj.user.user.phone_number}"
    user_display.short_description = "Foydalanuvchi"