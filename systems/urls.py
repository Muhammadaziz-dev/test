from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    StockTransferViewSet,
    ProductSaleViewSet,
    ProductEntrySystemViewSet
)

router = DefaultRouter()
router.register(r'stock-transfers', StockTransferViewSet, basename='stock-transfer')
router.register(r'sales', ProductSaleViewSet, basename='sales')
router.register(r'product-entries', ProductEntrySystemViewSet, basename='product-entries')

urlpatterns = [
    path('', include(router.urls)),
]
