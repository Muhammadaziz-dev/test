from django.urls import path, include
from .views import LoginView, AccessTokenVerifyView, CustomTokenRefreshView
from rest_framework.routers import DefaultRouter
from accounts.views import UserProfileViewSet

router = DefaultRouter()
router.register(r"profile", UserProfileViewSet, basename="user-profile")

urlpatterns = [
    path('login/', LoginView.as_view(), name='user-login'),
    path('device/', include('device.urls')),
    path("token/verify/", AccessTokenVerifyView.as_view(), name="token_verify"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path('', include(router.urls)),
]
