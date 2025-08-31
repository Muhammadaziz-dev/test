from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from .models import Device
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import DeviceSerializer


class DeviceListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_classes = None

    def get(self, request):
        devices = Device.objects.filter(user=request.user, is_active=True).order_by('-last_login')
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)


class DeviceDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            device = Device.objects.get(pk=pk, user=request.user, is_active=True)
        except Device.DoesNotExist:
            raise NotFound("Qurilma topilmadi.")

        if device.refresh_token:
            try:
                token = RefreshToken(device.refresh_token)
                token.blacklist()
            except Exception:
                pass

        device.is_active = False
        device.refresh_token = None
        device.save(update_fields=["is_active", "refresh_token"])

        return Response({"detail": "Qurilma tizimdan chiqarildi."}, status=status.HTTP_204_NO_CONTENT)

class LogoutAllDevicesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            try:
                BlacklistedToken.objects.get_or_create(token=token)
            except Exception:
                pass

        Device.objects.filter(user=user).update(is_active=False, refresh_token=None)

        return Response({"detail": "Siz barcha qurilmalardan muvaffaqiyatli chiqdingiz."}, status=status.HTTP_200_OK)