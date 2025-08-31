from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, StockEntryViewSet, PropertiesViewSet, ImagesViewSet,
    CountTypeChoicesView, ProductTrashViewSet, ExportProductsExcelAPI, ExportTaskLogListView
)

router = DefaultRouter()

router.register(r'products', ProductViewSet, basename='product')
router.register(r'trash', ProductTrashViewSet, basename='product-trash')
router.register(r'stock', StockEntryViewSet, basename='stocks_product')
router.register(r'properties', PropertiesViewSet, basename='properties_product')
router.register(r'images', ImagesViewSet, basename='images_product')

urlpatterns = [
    path('', include(router.urls)),
    path('meta/count-types/', CountTypeChoicesView.as_view(), name='count-type-choices'),
    path('export/create/', ExportProductsExcelAPI.as_view(), name='export-products'),
    path('export/logs/', ExportTaskLogListView.as_view(), name='export-log-list'),
]
