from __future__ import annotations

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from groups.models import GrupaProduktow

from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    """GET /api/alerts/ + retrieve/update/delete by pk.

    Creates live under POST /api/groups/{group_id}/alerts/ via
    GrupaAlertsView so the alert is bound to a specific group the user
    owns.
    """

    serializer_class = AlertSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get_queryset(self) -> QuerySet[Alert]:
        return (
            Alert.objects.filter(grupa__uzytkownik_id=self.request.user.pk)
            .select_related("grupa")
            .order_by("-utworzono")
        )


class GrupaAlertsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AlertSerializer

    def post(self, request: Request, group_id: int) -> Response:
        grupa = get_object_or_404(GrupaProduktow, id=group_id, uzytkownik_id=request.user.pk)
        serializer = AlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(grupa=grupa)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
