# # analytics/urls.py
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import (
#     OrderAnalyticsViewSet,
#     ProductAnalyticsViewSet,
#     DebtAnalyticsViewSet,
#     StoreAnalyticsViewSet, SellerAnalyticsViewSet,
# )
#
# router = DefaultRouter()
# router.register(r'orders', OrderAnalyticsViewSet, basename='orders-analytics')
# router.register(r'products', ProductAnalyticsViewSet, basename='products-analytics')
# router.register(r'debts', DebtAnalyticsViewSet, basename='debts-analytics')
# router.register(r'store', StoreAnalyticsViewSet, basename='store-analytics')
# router.register(r'sellers', SellerAnalyticsViewSet, basename='sellers-analytics')
#
# urlpatterns = [
#     path('', include(router.urls)),
# ]


from django.urls import path
from .api import SalesAnalyticsView, ExpenseAnalyticsView, CashAnalyticsView, DebtAnalyticsView, ProductAnalyticsView, \
    RefundAnalyticsView, PlatformAnalyticsView

urlpatterns = [
    path("sales/", SalesAnalyticsView.as_view(), name="sales-analytics"),
    path("expenses/", ExpenseAnalyticsView.as_view(), name="expense-analytics"),
    path("cashbox/", CashAnalyticsView.as_view(), name="cash-analytics"),
    path("debt/", DebtAnalyticsView.as_view(), name="debt-analytics"),
    path("products/", ProductAnalyticsView.as_view(), name="product-analytics"),
    path("refunds/", RefundAnalyticsView.as_view(), name="refund-analytics"),
    path("overview/", PlatformAnalyticsView.as_view(), name="platform-analytics-overview"),
]
