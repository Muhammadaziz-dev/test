# loan/urls.py
from django.urls import path, include, re_path
from rest_framework_nested.routers import SimpleRouter, NestedSimpleRouter

from .views import (
    DebtUserViewSet,
    DebtDocumentViewSet,
    DocumentProductViewSet,
    DebtUserMessageView,
)

# Root: /platform/<store_id>/debt/debtors/
root_router = SimpleRouter()
root_router.register(r"debtors", DebtUserViewSet, basename="debtors")

# /debtors/{debtor_pk}/documents/
debtor_router = NestedSimpleRouter(root_router, r"debtors", lookup="debtor")
debtor_router.register(r"documents", DebtDocumentViewSet, basename="debtor-documents")

# /debtors/{debtor_pk}/documents/{document_pk}/products/
documents_router = NestedSimpleRouter(debtor_router, r"documents", lookup="document")
documents_router.register(
    r"products", DocumentProductViewSet, basename="document-products"
)

urlpatterns = [
    *root_router.urls,
    *debtor_router.urls,
    *documents_router.urls,
    # Manual message endpoint
    re_path(
        r"^debtors/send-message/$",
        DebtUserMessageView.as_view(),
        name="debtuser-send-message",
    ),
]
