from rest_framework import serializers
from cashbox.models import Cashbox, CashTransaction


class CashboxSerializer(serializers.ModelSerializer):
    store_id = serializers.IntegerField(source='store.id', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = Cashbox
        fields = ['id', 'store_id', 'store_name', 'balance']
        read_only_fields = ['id', 'balance', 'store_id', 'store_name']


class CashTransactionSerializer(serializers.ModelSerializer):
    direction = serializers.SerializerMethodField()

    class Meta:
        model = CashTransaction
        fields = [
            'id', 'cashbox', 'amount', 'is_out', 'direction',
            'created_at', 'note', 'order', 'manual_source', 'exchange_rate',
        ]
        read_only_fields = ['id', 'created_at', 'direction']

    def get_direction(self, obj):
        return "out" if obj.is_out else "into"
