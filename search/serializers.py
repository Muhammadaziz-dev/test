
from rest_framework import serializers
from django.conf import settings
from product.models import Product

class ProductSearchSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'barcode',
            'out_price', 'count', 'warehouse_count',
            'category_id', 'thumbnail',
        ]

    def get_thumbnail(self, obj):
        rel = getattr(obj, 'thumb', None)
        if not rel:
            return None
        request = self.context.get('request')
        url = f"{settings.MEDIA_URL}{rel}".replace('//', '/')
        return request.build_absolute_uri(url) if request else url
