from django.urls import path
from .views import DeviceListView, DeviceDeleteView, LogoutAllDevicesView

urlpatterns = [
    path('', DeviceListView.as_view(), name='device-list'),
    path('<int:pk>/', DeviceDeleteView.as_view(), name='device-delete'),
    path('logout/', LogoutAllDevicesView.as_view(), name='logout-all'),
]