from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from staffs.mixins import StoreIDMixin
from staffs.permissions import StoreStaffPermission
from .models import Product, Properties, StockEntry, ProductImage, COUNT_TYPE_CHOICES, ExportTaskLog
from .serializers import (
    ProductDetailSerializer, ProductCreateSerializer, ProductListSerializer,
    StockEntrySerializer, ProductUpdateSerializer, PropertiesSerializer,
    ProductImageSerializer, ExportTaskLogSerializer
)
from product.tasks import export_products_excel
from rest_framework.permissions import IsAuthenticated
import uuid, re


class ExportThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        return request.user.is_staff or super().allow_request(request, view)


class ProductViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'barcode']
    filterset_fields = ['category', 'in_stock']
    ordering_fields = ['name', 'date_added', 'out_price']
    ordering = ['-date_added']

    def get_queryset(self):
        store_id = self.get_store_id()
        if not store_id:
            return Product.objects.none()
        return Product.objects.active().filter(store=store_id).prefetch_related(
            'images', 'properties', 'stock_entries'
        ).select_related('category')

    def get_serializer_class(self):
        match self.action:
            case 'list': return ProductListSerializer
            case 'retrieve': return ProductDetailSerializer
            case 'create': return ProductCreateSerializer
            case 'update' | 'partial_update': return ProductUpdateSerializer
            case _: return ProductDetailSerializer

    def perform_create(self, serializer):
        serializer.save(store=self.get_store())

    def create(self, request, *args, **kwargs):
        def transform(data):
            result = {}
            for key, value in data.items():
                value = value[0] if isinstance(value, list) and len(value) == 1 else value
                if '[' in key:
                    parts = [p for p in re.split(r'\[|\]', key) if p]
                    current = result
                    for i, part in enumerate(parts[:-1]):
                        next_is_index = parts[i + 1].isdigit()
                        if part.isdigit():
                            part = int(part)
                            while len(current) <= part:
                                current.append({} if next_is_index else {})
                            current = current[part]
                        else:
                            if part not in current:
                                current[part] = [] if next_is_index else {}
                            current = current[part]
                    last = parts[-1]
                    if isinstance(current, list):
                        if not current or not isinstance(current[-1], dict):
                            current.append({})
                        current[-1][last] = value
                    else:
                        current[last] = value
                else:
                    result[key] = value
            return result

        transformed_data = transform(request.data)
        transformed_data.update(request.FILES)
        print("[TRANSFORMED DATA]", transformed_data)

        if 'images' in request.FILES:
            images = request.FILES.getlist('images')
            transformed_data['images'] = [{'image': img} for img in images]

        serializer = self.get_serializer(data=transformed_data)

        if not serializer.is_valid():
            print("[VALIDATION ERROR]", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        self.perform_create(serializer)

        print("[PRODUCT CREATED SUCCESSFULLY]", serializer.data)
        print(f"[BY USER] {request.user} (id={request.user.id})")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def stock(self, request, store_id=None, pk=None):
        entries = self.get_object().stock_entries.order_by('-created_at')
        return Response(StockEntrySerializer(entries, many=True).data)

    @action(detail=True, methods=['post'], url_path='stock-add')
    def add_stock_entry(self, request, store_id=None, pk=None):
        serializer = StockEntrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=self.get_object())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def properties(self, request, store_id=None, pk=None):
        properties = self.get_object().properties.all()
        return Response(PropertiesSerializer(properties, many=True).data)

    @action(detail=True, methods=['post'], url_path='properties-add')
    def add_property(self, request, store_id=None, pk=None):
        serializer = PropertiesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=self.get_object())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def images(self, request, store_id=None, pk=None):
        images = self.get_object().images.all()
        return Response(ProductImageSerializer(images, many=True).data)

    @action(detail=True, methods=['post'], url_path='images-add')
    def add_images(self, request, store_id=None, pk=None):
        serializer = ProductImageSerializer(data=request.data, many=isinstance(request.data, list))
        if serializer.is_valid():
            serializer.save(product=self.get_object())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StockEntryViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    serializer_class = StockEntrySerializer

    def get_queryset(self):
        return StockEntry.objects.filter(product__store_id=self.get_store_id()).select_related('product')


class PropertiesViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    serializer_class = PropertiesSerializer

    def get_queryset(self):
        return Properties.objects.filter(product__store_id=self.get_store_id()).select_related('product')


class ImagesViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    serializer_class = ProductImageSerializer

    def get_queryset(self):
        return ProductImage.objects.filter(product__store_id=self.get_store_id()).select_related('product')


class CountTypeChoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id=None, pk=None):
        return Response([{'value': v, 'label': l} for v, l in COUNT_TYPE_CHOICES])


class ProductTrashViewSet(StoreIDMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, StoreStaffPermission]
    lookup_field = 'pk'

    def get_queryset(self):
        return Product.all_objects.filter(store=self.get_store_id(), is_deleted=True)

    def get_serializer_class(self):
        return ProductListSerializer if self.action == 'list' else ProductDetailSerializer

    @action(detail=True, methods=['post'])
    def restore(self, request, store_id=None, pk=None):
        product = self.get_queryset().filter(pk=pk).first()
        if not product:
            return Response({"detail": "Product not found or not deleted."}, status=status.HTTP_404_NOT_FOUND)
        if not product.is_deleted:
            return Response({"detail": "Product already active."}, status=status.HTTP_400_BAD_REQUEST)
        product.restore()
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=['delete'])
    def delete(self, request, store_id=None, pk=None):
        product = self.get_queryset().filter(pk=pk).first()
        if not product:
            return Response({"detail": "Product not found or not deleted."}, status=status.HTTP_404_NOT_FOUND)
        product.hard_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExportProductsExcelAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ExportThrottle]

    def post(self, request, store_id):
        task_id = str(uuid.uuid4())
        task_log, _ = ExportTaskLog.objects.get_or_create(
            task_id=task_id,
            defaults={
                'store_id': store_id,
                'user': request.user,
                'status': 'PENDING'
            }
        )
        export_products_excel.apply_async(kwargs={
            'store_id': store_id,
            'task_id': task_id,
            'user_id': request.user.id,
        })
        return Response({
            "status": "processing",
            "task_id": task_id,
            "detail": "Excel fayl eksporti fon rejimida bajarilmoqda."
        }, status=status.HTTP_202_ACCEPTED)


class ExportTaskLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        logs = ExportTaskLog.objects.filter(store_id=store_id).order_by('-created_at')[:50]
        return Response(ExportTaskLogSerializer(logs, many=True).data)
