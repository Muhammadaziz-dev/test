# loan/urls_offers.py (new)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_offers import DebtImportOfferViewSet

router = DefaultRouter()
router.register(r"offers", DebtImportOfferViewSet, basename="debt-import-offer")

urlpatterns = [
    path("", include(router.urls)),
]
