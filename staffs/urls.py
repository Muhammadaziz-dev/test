from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import StoreStaffViewSet

router = DefaultRouter()
router.register(r'', StoreStaffViewSet, basename='store-staff')

urlpatterns = router.urls