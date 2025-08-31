from rest_framework import serializers
from .models import StockTransfer, ProductSale, ProductEntrySystem
from product.models import Product
from product.serializers import ProductListSerializer


class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = '__all__'
        read_only_fields = ['auto']
        depth = 1

    def create(self, validated_data):
        instance = StockTransfer(**validated_data)
        instance.save()
        return instance


class ProductSaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSale
        fields = '__all__'
        depth = 1


def validate(self, data):
    data['total_price'] = data['unit_price'] * data['quantity']
    if data['product']:
        cost = data['product'].get_cost_price()
        data['profit'] = data['total_price'] - (cost * data['quantity'])
    return data


class ProductEntrySystemWriteSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = ProductEntrySystem
        fields = '__all__'
        read_only_fields = ['date', 'exchange_rate', 'store']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        store = self.context.get('store')
        if store:
            self.fields['product'].queryset = Product.objects.filter(store=store)

    def validate(self, data):
        store = self.context.get('store')
        product = data.get('product')
        if store and product and product.store_id != store.id:
            raise serializers.ValidationError({'product': "Mahsulot ushbu do‘konga tegishli emas."})
        return data

class ProductEntrySystemReadSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = ProductEntrySystem
        fields = '__all__'
        depth = 1