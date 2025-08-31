from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlatformUserViewSet, RateUsdViewSet

router = DefaultRouter()
router.register('', PlatformUserViewSet)
router.register(r'rates', RateUsdViewSet, basename='rate-usd')

urlpatterns = [
    path('', include(router.urls)),
]