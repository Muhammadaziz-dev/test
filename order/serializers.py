from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from order.models import Order, ProductOrder
from product.models import Product
from product.serializers import ProductListSerializer


class ProductOrderSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = ProductOrder
        fields = [
            'id', 'product', 'product_id', 'quantity',
            'price', 'currency', 'exchange_rate'
        ]
        read_only_fields = ['id', 'exchange_rate',]


class OrderListSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=20, decimal_places=6, read_only=True)
    total_profit = serializers.DecimalField(max_digits=20, decimal_places=6, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'phone_number', 'first_name', 'last_name', 'total_price', 'total_profit', 'created_at', 'unreturned_income', 'paid_amount', 'change_given', 'change_amount', "currency_change", 'exchange_rate'
        ]
        read_only_fields = ['id', 'exchange_rate', ]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = ProductOrderSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'phone_number', 'first_name', 'last_name',
            'currency', 'exchange_rate', 'payment_type',
            'paid_amount', 'change_given', 'change_amount',
            'total_price', 'total_profit', 'unreturned_income',
            'items', 'created_at', 'is_deleted', 'deleted_at',  "currency_change"
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.ModelSerializer):
    items = ProductOrderSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'store', 'phone_number', 'first_name', 'last_name',
            'currency', 'exchange_rate', 'payment_type',
            'paid_amount', 'change_given', 'items', "currency_change", 'change_amount'
        ]
        read_only_fields = ['id', 'created_at', 'total_price', 'total_profit',  'store', 'exchange_rate',]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Buyurtma uchun kamida 1 ta mahsulot kerak.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            ProductOrder.objects.create(order=order, **item_data)

        order.calculate_totals_and_change()
        order.save(update_fields=['total_price', 'total_profit', 'change_amount'])
        return order
