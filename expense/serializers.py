from rest_framework import serializers
from .models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    full_reason = serializers.CharField(source='get_full_reason', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'store', 'store_name',
            'reason', 'custom_reason', 'full_reason',
            'amount', 'currency', 'exchange_rate',
            'note', 'date', 'cash_transaction'
        ]
        read_only_fields = ['id', 'date', 'cash_transaction', 'store_name', 'full_reason', 'store']