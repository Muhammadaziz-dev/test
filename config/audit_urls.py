# audit/urls.py
from rest_framework.routers import DefaultRouter
from .views import LogEntryViewSet

router = DefaultRouter()
router.register(r'logs', LogEntryViewSet, basename='audit-log')

urlpatterns = router.urls
