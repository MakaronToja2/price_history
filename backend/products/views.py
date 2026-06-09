from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from groups.models import GrupaProduktow
from scrapers.detection import UnsupportedPlatformError, detect_platforma
from scrapers.tasks import fetch_product_price

from .models import Platforma, Produkt
from .serializers import AddProductSerializer, ProduktSerializer


class GroupProductsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AddProductSerializer

    def get(self, request: Request, group_id: int) -> Response:
        grupa = get_object_or_404(GrupaProduktow, id=group_id, uzytkownik_id=request.user.pk)
        produkty = grupa.produkty.select_related("platforma").all()
        return Response(ProduktSerializer(produkty, many=True).data)

    def post(self, request: Request, group_id: int) -> Response:
        grupa = get_object_or_404(GrupaProduktow, id=group_id, uzytkownik_id=request.user.pk)

        serializer = AddProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data["url"]

        try:
            wykryta = detect_platforma(url)
        except UnsupportedPlatformError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            platforma = Platforma.objects.get(nazwa=wykryta.platforma)
        except Platforma.DoesNotExist:
            return Response(
                {"detail": f"Platforma {wykryta.platforma!r} nie istnieje."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Produkt.objects.filter(
            grupa=grupa,
            platforma=platforma,
            zewnetrzny_id=wykryta.identyfikator,
        ).exists():
            return Response(
                {"detail": "Produkt już istnieje w tej grupie."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        produkt = Produkt.objects.create(
            grupa=grupa,
            platforma=platforma,
            zewnetrzny_id=wykryta.identyfikator,
            url=url,
        )

        async_result = fetch_product_price.delay(produkt.id)

        data = ProduktSerializer(produkt).data
        data["task_id"] = async_result.id
        return Response(data, status=status.HTTP_201_CREATED)


class GroupProductDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request: Request, group_id: int, product_id: int) -> Response:
        """Soft-delete: mark inactive so history in TimescaleDB stays intact."""
        produkt = get_object_or_404(
            Produkt,
            id=product_id,
            grupa_id=group_id,
            grupa__uzytkownik_id=request.user.pk,
        )
        produkt.aktywny = False
        produkt.save(update_fields=["aktywny"])
        return Response(status=status.HTTP_204_NO_CONTENT)
