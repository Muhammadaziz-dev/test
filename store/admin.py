from django.contrib import admin
from .models import Store

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner', 'phone_number', 'get_balance', 'created_at']
    readonly_fields = ['created_at']