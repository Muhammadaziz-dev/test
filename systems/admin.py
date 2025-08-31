# systems/admin.py

from django.contrib import admin
from .models import StockTransfer, ProductSale, ProductEntrySystem


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'auto', 'note', 'created_at')
    list_filter = ('auto', 'created_at')
    search_fields = ('product__name', 'note')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(ProductSale)
class ProductSaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'unit_price', 'total_price', 'profit', 'currency', 'created_at')
    list_filter = ('currency', 'created_at')
    search_fields = ('product__name', 'order__id')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(ProductEntrySystem)
class ProductEntrySystemAdmin(admin.ModelAdmin):
    list_display = ('product', 'count', 'unit_price', 'currency', 'exchange_rate', 'is_warehouse', 'date')
    list_filter = ('currency', 'is_warehouse', 'date')
    search_fields = ('product__name',)
    readonly_fields = ('date', 'exchange_rate')
    date_hierarchy = 'date'
    autocomplete_fields = ['product']