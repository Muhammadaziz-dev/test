from django.urls import path
from cashbox.views import CashboxDetailView, CashTransactionListView

urlpatterns = [
    path('', CashboxDetailView.as_view(), name='cashbox-detail'),
    path('transactions/', CashTransactionListView.as_view(), name='cashbox-transactions'),
]