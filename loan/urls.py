# loan/urls.py
from rest_framework_nested.routers import SimpleRouter, NestedSimpleRouter
from .views import DebtUserViewSet, DebtDocumentViewSet, DocumentProductViewSet

# Root: /platform/<store_id>/debt/
# 1) /debtors/
router = SimpleRouter()
router.register(r'debtors', DebtUserViewSet, basename='debtors')

# 2) /debtors/{debtor_pk}/documents/
debtors_router = NestedSimpleRouter(router, r'debtors', lookup='debtor')
debtors_router.register(r'documents', DebtDocumentViewSet, basename='debtor-documents')

# 3) /debtors/{debtor_pk}/documents/{document_pk}/products/
documents_router = NestedSimpleRouter(debtors_router, r'documents', lookup='document')
documents_router.register(r'products', DocumentProductViewSet, basename='document-products')

urlpatterns = [
    *router.urls,
    *debtors_router.urls,
    *documents_router.urls,
]
