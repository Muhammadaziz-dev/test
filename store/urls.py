from rest_framework.routers import DefaultRouter
from store.views import StoreViewSet

router = DefaultRouter()
router.register(r'', StoreViewSet, basename='store')

urlpatterns = router.urls