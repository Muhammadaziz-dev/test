from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db import transaction
from .models import Product, ProductImage, Properties, StockEntry, ExportTaskLog, WasteEntry
from .tasks import export_products_excel
import uuid

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class PropertiesInline(admin.TabularInline):
    model = Properties
    extra = 1

class StockEntryInline(admin.TabularInline):
    model = StockEntry
    extra = 1
    readonly_fields = ('created_at', "exchange_rate",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, PropertiesInline, StockEntryInline]
    list_display = (
        'id', 'name', 'sku', 'barcode', 'enter_price', 'out_price',
        'currency', 'in_stock', 'count', 'date_added',
        'is_deleted', 'deleted_at'
    )
    list_filter = ('in_stock', 'currency', 'date_added', 'is_deleted')
    search_fields = ('name', 'sku', 'barcode')
    readonly_fields = ('date_added', "exchange_rate", 'enter_price', 'count', 'warehouse_count')
    list_display_links = ('id', 'name')
    autocomplete_fields = ['category']

    actions = [
        'toggle_in_stock_status',
        'generate_sku_and_barcode',
        'restore_products',
        'hard_delete_products',
        'async_export_to_excel'
    ]

    def get_queryset(self, request):
        return Product.all_objects.select_related('category').prefetch_related('images', 'properties')

    @admin.action(description=_("Toggle 'in_stock' status for selected products"))
    def toggle_in_stock_status(self, request, queryset):
        for product in queryset:
            product.in_stock = not product.in_stock
            product.save(update_fields=['in_stock'])
        self.message_user(request, f"{queryset.count()} products updated.")

    @admin.action(description=_("Generate missing SKU and barcode"))
    def generate_sku_and_barcode(self, request, queryset):
        updated = 0
        for product in queryset:
            if not product.sku or not product.barcode:
                product.save()
                updated += 1
        self.message_user(request, f"{updated} products updated with SKU/barcode.")

    @admin.action(description=_("Restore soft-deleted products"))
    def restore_products(self, request, queryset):
        updated = queryset.update(is_deleted=False, deleted_at=None)
        self.message_user(request, f"{updated} products restored.")

    @admin.action(description=_("Permanently delete selected products"))
    def hard_delete_products(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} products permanently deleted.")

    @admin.action(description=_("Asinxron eksport (Excel + Rasm)"))
    def async_export_to_excel(modeladmin, request, queryset):
        store_ids = queryset.values_list('store_id', flat=True).distinct()
        if len(store_ids) != 1:
            modeladmin.message_user(
                request,
                "Iltimos, faqat bitta do‘konga tegishli mahsulotlarni tanlang.",
                level=messages.ERROR
            )
            return

        store_id = store_ids[0]
        user = request.user
        task_id = str(uuid.uuid4())

        def launch_task():
            export_products_excel.delay(store_id=store_id, task_id=task_id, user_id=user.id)

        ExportTaskLog.objects.create(
            task_id=task_id,
            store_id=store_id,
            user=user,
            status='PENDING'
        )

        transaction.on_commit(launch_task)

        modeladmin.message_user(
            request,
            f"Excel eksport vazifasi yuborildi. Task ID: {task_id}. Natijani admin paneldan kuzatishingiz mumkin.",
            level=messages.SUCCESS
        )

    def delete_model(self, request, obj):
        obj.soft_delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.soft_delete()

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is not None:
            obj.soft_delete()
            self.message_user(request, f"Product '{obj.name}' soft-deleted.")
            return HttpResponseRedirect(reverse('admin:category_product_changelist'))
        return super().delete_view(request, object_id, extra_context)

    def has_delete_permission(self, request, obj=None):
        return True

@admin.register(ExportTaskLog)
class ExportTaskLogAdmin(admin.ModelAdmin):
    list_display = ("task_id", "user", "store_id", "status", "created_at", "completed_at")
    search_fields = ("task_id",)
    list_filter = ("status", "created_at")

@admin.register(WasteEntry)
class WasteEntryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'reason', 'refund', 'created_at')
    list_filter = ('created_at', 'reason', 'product')
    search_fields = ('product__name', 'reason', 'refund__id')
    autocomplete_fields = ('product', 'refund')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('product', 'quantity', 'reason', 'refund')
        }),
        ('Qo‘shimcha maʼlumotlar', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser