# product/filters.py
from django.db.models import Q, F
from django_filters import rest_framework as filters
from .models import Product

class ProductSearchFilter(filters.FilterSet):
    q = filters.CharFilter(method='text_search', label="Qidiruv")
    sku = filters.CharFilter(field_name='sku', lookup_expr='iexact')
    barcode = filters.CharFilter(field_name='barcode', lookup_expr='iexact')
    category = filters.NumberFilter(field_name='category_id')
    count_type = filters.CharFilter(field_name='count_type', lookup_expr='iexact')
    min_price = filters.NumberFilter(field_name='out_price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='out_price', lookup_expr='lte')

    in_stock = filters.BooleanFilter(field_name='in_stock')
    available_only = filters.BooleanFilter(method='filter_available_only',
                                           label="Faqat mavjud (count+warehouse_count > 0)")

    class Meta:
        model = Product
        fields = ['sku', 'barcode', 'category', 'count_type', 'in_stock']

    def text_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(sku__icontains=value) |
            Q(barcode__icontains=value) |
            Q(description__icontains=value)
        )

    def filter_available_only(self, queryset, name, value):
        if not value:
            return queryset
        # available if either shelf or warehouse has quantity
        return queryset.exclude(count=0, warehouse_count=0)
