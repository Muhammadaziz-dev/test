from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from order.views import OrderViewSet, OrderItemsViewSet, OrderTrashViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'items', OrderItemsViewSet, basename='order-items')
router.register(r'trash', OrderTrashViewSet, basename='order-trash')
# orders_router = NestedDefaultRouter(router, r'orders', lookup='order')
# orders_router.register(r'items', OrderItemViewSet, basename='order-items')

urlpatterns = [
    path('', include(router.urls)),
    # path('', include(orders_router.urls)),
]

