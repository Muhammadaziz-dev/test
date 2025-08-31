from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductSearchViewSet, CategorySearchView

router = DefaultRouter()
router.register(r'product', ProductSearchViewSet, basename='product-search')

urlpatterns = [
    path('', include(router.urls)),
    path('category/', CategorySearchView.as_view(), name='category-search'),
]
