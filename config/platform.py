from django.urls import path, include

urlpatterns = [
    path('logs/', include('config.audit_urls')),
    path('user/', include('platform_user.urls')),
    path('accounts/', include('accounts.urls')),
    path('store/', include('store.urls')),
    path('categories/', include('category.urls')),
    path('<int:store_id>/', include([
        path("analytics/", include('analytics.urls')),
        path('search/', include('search.urls')),
        path('cashbox/', include('cashbox.urls')),
        path('staffs/', include('staffs.urls')),
        path('orders/', include('order.urls')),
        path('products/', include('product.urls')),
        path('refunds/', include('refund.urls')),
        path('system/', include('systems.urls')),
        path('expense/', include('expense.urls')),
        path('debt/', include('loan.urls'))
    ])),
]
