from __future__ import annotations

from datetime import UTC, datetime, timedelta

from django.db.models import Count, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from analytics.repositories import HistoriaCenRepository
from scrapers.tasks import fetch_product_price

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

    @action(
        detail=True,
        methods=["post"],
        throttle_classes=(ScopedRateThrottle,),
    )
    def refresh(self, request: Request, pk: int | None = None) -> Response:  # noqa: ARG002
        """Enqueue a fresh fetch for every produkt in the group."""
        grupa = self.get_object()
        task_ids = [fetch_product_price.delay(p.id).id for p in grupa.produkty.filter(aktywny=True)]
        return Response(
            {"message": "Refresh queued", "task_ids": task_ids},
            status=status.HTTP_202_ACCEPTED,
        )

    refresh.throttle_scope = "refresh-group"  # type: ignore[attr-defined]

    @action(detail=True, methods=["get"])
    def prices(self, request: Request, pk: int | None = None) -> Response:  # noqa: ARG002
        """Lowest-price history across every produkt in the group."""
        grupa = self.get_object()
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            return Response(
                {"detail": "Parametr 'days' musi być liczbą."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        days = max(1, min(days, 365))
        since = datetime.now(UTC) - timedelta(days=days)

        repo = HistoriaCenRepository()
        dane: list[dict[str, object]] = []
        for produkt in grupa.produkty.select_related("platforma").all():
            rows = repo.get_lowest_history(produkt_id=produkt.id, since=since)
            for row in rows:
                dane.append(
                    {
                        "czas": row["czas"],
                        "najnizsza_cena": str(row["cena"]),
                        "platforma": produkt.platforma.nazwa,
                        "sprzedawca": produkt.aktualny_najlepszy_sprzedawca or "",
                    }
                )
        dane.sort(key=lambda r: r["czas"], reverse=True)  # type: ignore[arg-type,return-value]

        return Response({"grupa_id": grupa.id, "dane": dane})

    @action(detail=True, methods=["get"])
    def comparison(self, request: Request, pk: int | None = None) -> Response:  # noqa: ARG002
        """Cross-platform snapshot of the cheapest seller per platform."""
        grupa = self.get_object()
        produkty = list(grupa.produkty.select_related("platforma").all())
        prices = [
            p.aktualna_najnizsza_cena for p in produkty if p.aktualna_najnizsza_cena is not None
        ]
        best_price = min(prices) if prices else None

        platformy = []
        for p in produkty:
            jest_najlepsza = best_price is not None and p.aktualna_najnizsza_cena == best_price
            platformy.append(
                {
                    "platforma": p.platforma.nazwa,
                    "produkt_id": p.id,
                    "najnizsza_cena": (
                        str(p.aktualna_najnizsza_cena)
                        if p.aktualna_najnizsza_cena is not None
                        else None
                    ),
                    "najlepszy_sprzedawca": p.aktualny_najlepszy_sprzedawca or "",
                    "liczba_sprzedawcow": p.liczba_sprzedawcow,
                    "jest_najlepsza": jest_najlepsza,
                }
            )

        return Response(
            {
                "grupa_id": grupa.id,
                "nazwa": grupa.nazwa,
                "najnizsza_cena_globalna": (
                    str(grupa.najnizsza_cena_globalna)
                    if grupa.najnizsza_cena_globalna is not None
                    else None
                ),
                "najlepsza_platforma": grupa.najlepsza_platforma,
                "platformy": platformy,
            }
        )
