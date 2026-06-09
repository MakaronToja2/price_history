from __future__ import annotations

from django.db.models import Count, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import GrupaProduktow
from .serializers import GrupaDetailSerializer, GrupaListSerializer


class GrupaViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ("aktywny",)
    search_fields = ("nazwa", "opis")

    def get_queryset(self) -> QuerySet[GrupaProduktow]:
        qs = GrupaProduktow.objects.filter(uzytkownik_id=self.request.user.pk).order_by(
            "-utworzono"
        )
        if self.action == "list":
            qs = qs.annotate(liczba_produktow=Count("produkty"))
        elif self.action == "retrieve":
            qs = qs.prefetch_related("produkty__platforma")
        return qs

    def get_serializer_class(self) -> type:
        if self.action == "retrieve":
            return GrupaDetailSerializer
        return GrupaListSerializer

    def perform_create(self, serializer) -> None:
        serializer.save(uzytkownik=self.request.user)
