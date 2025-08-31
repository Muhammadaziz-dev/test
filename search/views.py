# views.py
from rest_framework import mixins, viewsets, permissions
from django.db.models import Q, Case, When, Value, IntegerField, Subquery, OuterRef
from staffs.mixins import StoreIDMixin
from staffs.permissions import StoreStaffPermission
from product.models import Product, ProductImage
from .serializers import ProductSearchSerializer
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from category.models import Category
from category.serializers import CategorySerializer


class ProductSearchViewSet(StoreIDMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    serializer_class = ProductSearchSerializer
    pagination_class = None

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        q = (self.request.query_params.get('q') or '').strip()

        if not store_id:
            return Product.objects.none()

        qs = Product.objects.active().filter(store_id=store_id)

        thumb_sq = ProductImage.objects.filter(
            product_id=OuterRef('pk')
        ).order_by('id').values('thumbnail')[:1]

        if q:
            qs = qs.annotate(
                relevance=Case(
                    When(sku__iexact=q, then=Value(100)),
                    When(barcode__iexact=q, then=Value(100)),
                    When(name__istartswith=q, then=Value(50)),
                    When(sku__istartswith=q, then=Value(40)),
                    When(barcode__startswith=q, then=Value(40)),
                    When(name__icontains=q, then=Value(10)),
                    When(description__icontains=q, then=Value(5)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).filter(
                Q(name__icontains=q) |
                Q(sku__icontains=q) |
                Q(barcode__icontains=q) |
                Q(description__icontains=q)
            ).order_by('-relevance', 'name')
        else:
            qs = qs.order_by('name')

        qs = qs.annotate(thumb=Subquery(thumb_sq)).only(
            'id', 'name', 'sku', 'barcode',
            'out_price', 'count', 'warehouse_count', 'category_id'
        )
        return qs[:500]


class CategorySearchView(generics.ListAPIView):
    queryset = Category.objects.all()
    pagination_class = None
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'slug']
