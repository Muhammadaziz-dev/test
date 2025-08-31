from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Order, ProductOrder


class ProductOrderInline(admin.TabularInline):
    model = ProductOrder
    extra = 0
    readonly_fields = ('usd_price_display', 'usd_total_display', 'exchange_rate',)
    fields = ('product', 'quantity', 'price', 'currency', 'exchange_rate', 'usd_price_display', 'usd_total_display')
    show_change_link = True

    @admin.display(description="USD Narx")
    def usd_price_display(self, obj):
        return obj.get_price_usd()

    @admin.display(description="USD Umumiy")
    def usd_total_display(self, obj):
        return obj.get_total_usd()


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'phone_number',
        'total_price', 'total_profit', 'unreturned_income',
        'payment_type', 'currency',
        'is_deleted', 'deleted_at', 'created_at'
    )
    list_filter = (
        'store', 'currency', 'payment_type', 'is_deleted', 'created_at'
    )
    search_fields = (
        'phone_number', 'first_name', 'last_name', 'customer__phone_number'
    )
    readonly_fields = ('total_price', 'total_profit', 'unreturned_income', 'exchange_rate',)
    inlines = [ProductOrderInline]
    date_hierarchy = 'created_at'
    actions = ['restore_orders', 'hard_delete_orders']

    def get_queryset(self, request):
        return Order.all_objects.select_related('customer', 'store')

    @admin.display(description="Qaytarilmagan pul (foyda)")
    def unreturned_income(self, obj):
        return obj.unreturned_income

    @admin.action(description=_("Tanlangan buyurtmalarni qayta tiklash"))
    def restore_orders(self, request, queryset):
        count = sum(1 for order in queryset if order.is_deleted and order.restore())
        self.message_user(request, f"{count} ta buyurtma tiklandi.")

    @admin.action(description=_("Tanlangan buyurtmalarni butunlay o‘chirish (Hard delete)"))
    def hard_delete_orders(self, request, queryset):
        count = queryset.count()
        for order in queryset:
            order.hard_delete()
        self.message_user(request, f"{count} ta buyurtma butunlay o‘chirildi.")

    def delete_model(self, request, obj):
        obj.soft_delete()
        self.message_user(request, f"Buyurtma #{obj.pk} yumshoq o‘chirildi.")

    def delete_queryset(self, request, queryset):
        count = queryset.count()
        for obj in queryset:
            obj.soft_delete()
        self.message_user(request, f"{count} ta buyurtma yumshoq o‘chirildi.")

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            obj.soft_delete()
            self.message_user(request, f"Buyurtma #{obj.pk} yumshoq o‘chirildi.")
            return HttpResponseRedirect(reverse('admin:order_order_changelist'))
        return super().delete_view(request, object_id, extra_context)

    def has_delete_permission(self, request, obj=None):
        return True
from django.contrib import admin
from .models import ProductOrder

@admin.register(ProductOrder)
class ProductOrderAdmin(admin.ModelAdmin):
    search_fields = ['product__name']  # Optional: autocomplete uchun
