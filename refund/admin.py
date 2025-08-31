# refund/admin.py

from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import Refund

class RefundAdminForm(forms.ModelForm):
    class Meta:
        model = Refund
        fields = '__all__'

    def clean(self):
        data = super().clean()
        po = data.get('product_order')
        dp = data.get('document_product')
        # 1) Faqat bittasi bo‘lsin
        if bool(po) == bool(dp):
            raise ValidationError("Faqat bitta: order yoki debt document_product bo‘lishi kerak.")
        # 2) OTHER uchun custom_reason majburiy
        if data.get('reason_type') == 'OTHER' and not data.get('custom_reason'):
            raise ValidationError("Custom reason is required for 'Boshqa'.")
        return data


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    form = RefundAdminForm

    list_display = (
        'related_object',
        'reason_type',
        'quantity',
        'refund_price',
        'created_at',
    )
    list_filter = ('reason_type', 'created_at')
    search_fields = (
        'product_order__product__name',
        'document_product__product__name',
        'custom_reason',
    )
    autocomplete_fields = ['product_order', 'document_product']
    readonly_fields = ['created_at']

    def related_object(self, obj):
        if obj.product_order:
            return f"Order #{obj.product_order.order.pk} — {obj.product_order.product.name}"
        return f"DebtDoc #{obj.document_product.document.pk} — {obj.document_product.product.name}"
    related_object.short_description = 'Related To'
