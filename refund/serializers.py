from rest_framework import serializers
from .models import Refund

class RefundSerializer(serializers.ModelSerializer):
    # Yordamchi maydon: buyurtma yoki qarz hujjatini o‘qish uchun
    related_object = serializers.SerializerMethodField(read_only=True)
    # Agar modelda refund_price metodi bo‘lsa, uni SerializerMethodField orqali chiqaramiz
    refund_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Refund
        fields = [
            'id',
            'product_order',
            'document_product',
            'reason_type',
            'custom_reason',
            'quantity',
            'refund_price',
            'related_object',
            'created_at',
        ]
        read_only_fields = ['id', 'refund_price', 'related_object', 'created_at']

    def get_related_object(self, obj):
        if obj.product_order:
            return {
                'type': 'order',
                'order_id': obj.product_order.order.pk,
                'product': obj.product_order.product.name
            }
        if obj.document_product:
            return {
                'type': 'debt',
                'debt_document_id': obj.document_product.document.pk,
                'product': obj.document_product.product.name
            }
        return None

    def get_refund_price(self, obj):
        # model.metodini chaqiramiz
        return obj.refund_price()

    def validate(self, data):
        """
        1) Faqat bittasi: product_order yoki document_product bo‘lsin
        2) OTHER uchun custom_reason majburiy
        """
        po = data.get('product_order')
        dp = data.get('document_product')
        if bool(po) == bool(dp):
            raise serializers.ValidationError(
                "Faqat bitta: product_order yoki document_product to‘ldirilishi kerak."
            )
        if data.get('reason_type') == 'OTHER' and not data.get('custom_reason'):
            raise serializers.ValidationError(
                "Custom reason is required for reason_type='OTHER'."
            )
        return data
# 