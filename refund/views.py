from rest_framework import viewsets
from .models import Refund
from .serializers import RefundSerializer


class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer
