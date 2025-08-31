from django.db import transaction
from rest_framework import serializers
from .models import Product, ProductImage, Properties, StockEntry, ExportTaskLog
from decimal import Decimal, ROUND_HALF_UP




class ProductExcelSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "enter_price", "out_price",
            "currency", "in_stock", "count",
            "image",
        ]

    def get_image(self, product):
        first = product.images.first()
        return first.image.url if first else ""

MAX_IMAGE_SIZE_MB = 5

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'thumbnail']


    def validate_image(self, value):
        if value.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(f"Image size must be less than {MAX_IMAGE_SIZE_MB}MB.")
        return value


class PropertiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Properties
        fields = ['id', 'feature', 'value']


class StockEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = StockEntry
        fields = ['id', 'quantity', 'unit_price', 'currency', 'exchange_rate', 'created_at', 'product', 'is_warehouse']
        read_only_fields = ['id', 'created_at', 'product', 'exchange_rate', ]


class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    remainder = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'enter_price', 'out_price', 'date_added', 'warehouse_count',
            'in_stock', 'currency', 'count', 'description',
            'count_type', 'images', 'sku', 'barcode', 'exchange_rate', 'remainder', 'category'
        ]
        read_only_fields = ['id', 'date_added', 'enter_price', 'count', 'deleted_at']

    def get_remainder(self, obj):
        warehouse = obj.warehouse_count or 0
        count = obj.count or 0
        price = obj.enter_price or Decimal('0')
        remainder = (warehouse + count) * price
        if not isinstance(remainder, Decimal):
            remainder = Decimal(remainder)
        return remainder.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    properties = PropertiesSerializer(many=True, read_only=True)
    stock_entries = StockEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'enter_price', 'out_price', 'date_added',
            'in_stock', 'currency', 'count', 'description',
            'count_type', 'images', 'properties', 'exchange_rate',
            'stock_entries', 'sku', 'barcode', 'warehouse_count', 'category'
        ]
        read_only_fields = ['id', 'date_added', 'enter_price', 'count']


class ProductCreateSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, required=False)
    properties = PropertiesSerializer(many=True, required=False)
    stock = StockEntrySerializer(write_only=True, many=True, required=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'out_price', 'in_stock', 'description', 'stock', 'exchange_rate', 'warehouse_count',
            'count_type', 'store', 'images', 'properties', 'category'
        ]
        read_only_fields = ['id', 'date_added', 'store', 'exchange_rate', ]

    @transaction.atomic
    def create(self, validated_data):
        stock_data = validated_data.pop('stock')
        images_data = validated_data.pop('images', [])
        properties_data = validated_data.pop('properties', [])


        product = Product.objects.create(**validated_data)
        product.save()

        if properties_data:
            Properties.objects.bulk_create([Properties(product=product, **item) for item in properties_data])

        if stock_data:
            entries = []
            for item in stock_data:
                entry = StockEntry(product=product, **item)
                entry.full_clean()
                entries.append(entry)

            for entry in entries:
                entry.save()

            product.recalculate_average_cost()

        if images_data:
            for img in images_data:
                ProductImage.objects.create(product=product, **img)

        return product



class ProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'out_price', 'in_stock',
            'description', 'count_type', 'store', 'exchange_rate', 'category'
        ]
        read_only_fields = ['id', 'date_added', 'exchange_rate', ]


class ExportTaskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportTaskLog
        fields = [
            'task_id',
            'store_id',
            'status',
            'file_url',
            'error_message',
            'progress',
            'started_at',
            'completed_at',
            'created_at'
        ]
