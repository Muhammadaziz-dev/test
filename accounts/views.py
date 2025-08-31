from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import LoginSerializer
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins, permissions
from accounts.models import CustomUser
from accounts.serializers import UserInfoSerializer, UserUpdateSerializer
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, TokenError
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import AuthenticationFailed
from device.models import Device


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserProfileViewSet(mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserInfoSerializer
        return UserUpdateSerializer





class AccessTokenVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("access")

        if not token:
            return Response({"detail": _("Access token yuborilmadi.")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            AccessToken(token)
            return Response({"valid": True}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"valid": False}, status=status.HTTP_401_UNAUTHORIZED)


class CustomTokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"detail": _("Refresh token yuborilmadi.")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(refresh_token=refresh_token)
        except Device.DoesNotExist:
            raise AuthenticationFailed(_("Bunday refresh token mavjud emas yoki qurilmaga bog‘lanmagan."))

        try:
            refresh = RefreshToken(refresh_token)
        except TokenError:
            raise AuthenticationFailed(_("Refresh token noto‘g‘ri yoki muddati tugagan."))

        new_refresh_token = str(refresh)
        new_access_token = str(refresh.access_token)

        device.refresh_token = new_refresh_token
        device.save(update_fields=["refresh_token"])

        return Response({
            "access": new_access_token,
            "refresh": new_refresh_token,
        }, status=status.HTTP_200_OK)

