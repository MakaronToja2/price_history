from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from analytics.repositories import HistoriaCenRepository, PomiarCeny
from groups.models import GrupaProduktow
from products.models import Platforma, Produkt
from users.models import User

pytestmark = pytest.mark.django_db(databases=["default", "timeseries"])


@pytest.fixture(autouse=True)
def _clean() -> None:
    HistoriaCenRepository().truncate()


@pytest.fixture
def produkty(user: User, group: GrupaProduktow) -> list[Produkt]:
    allegro = Platforma.objects.get(nazwa="allegro")
    amazon = Platforma.objects.get(nazwa="amazon")
    return [
        Produkt.objects.create(
            grupa=group,
            platforma=allegro,
            zewnetrzny_id="P-1",
            url="https://allegro.pl/oferta/foo-1",
            aktualna_najnizsza_cena=Decimal("99.00"),
            aktualny_najlepszy_sprzedawca="TanioPL",
            liczba_sprzedawcow=3,
        ),
        Produkt.objects.create(
            grupa=group,
            platforma=amazon,
            zewnetrzny_id="ASIN-1",
            url="https://amazon.pl/dp/ASIN-1",
            aktualna_najnizsza_cena=Decimal("110.00"),
            aktualny_najlepszy_sprzedawca="AmazonSeller",
            liczba_sprzedawcow=5,
        ),
    ]


class TestRefreshAction:
    def test_enqueues_fetch_for_each_active_product(
        self,
        client: APIClient,
        group: GrupaProduktow,
        produkty: list[Produkt],
    ) -> None:
        with patch("groups.views.fetch_product_price.delay") as mock_delay:
            mock_delay.return_value.id = "task-id"
            response = client.post(f"/api/groups/{group.id}/refresh/")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert mock_delay.call_count == len(produkty)
        body = response.json()
        assert "Refresh queued" in body["message"]
        assert len(body["task_ids"]) == len(produkty)

    def test_skips_inactive_products(
        self,
        client: APIClient,
        group: GrupaProduktow,
        produkty: list[Produkt],
    ) -> None:
        produkty[0].aktywny = False
        produkty[0].save(update_fields=["aktywny"])

        with patch("groups.views.fetch_product_price.delay") as mock_delay:
            mock_delay.return_value.id = "task-id"
            client.post(f"/api/groups/{group.id}/refresh/")

        assert mock_delay.call_count == 1

    def test_other_users_group_404(self, client: APIClient, other_user: User) -> None:
        foreign = GrupaProduktow.objects.create(uzytkownik=other_user, nazwa="F")
        response = client.post(f"/api/groups/{foreign.id}/refresh/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPricesAction:
    def test_returns_lowest_history(
        self,
        client: APIClient,
        group: GrupaProduktow,
        produkty: list[Produkt],
    ) -> None:
        repo = HistoriaCenRepository()
        now = datetime.now(UTC)
        repo.insert_pomiary(
            [
                PomiarCeny(
                    czas=now - timedelta(hours=2),
                    produkt_id=produkty[0].id,
                    cena=Decimal("100"),
                ),
                PomiarCeny(
                    czas=now - timedelta(hours=2),
                    produkt_id=produkty[0].id,
                    cena=Decimal("95"),
                ),
                PomiarCeny(
                    czas=now - timedelta(hours=1),
                    produkt_id=produkty[1].id,
                    cena=Decimal("105"),
                ),
                PomiarCeny(
                    czas=now - timedelta(hours=1),
                    produkt_id=produkty[1].id,
                    cena=Decimal("99"),
                ),
            ]
        )

        response = client.get(f"/api/groups/{group.id}/prices/")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["grupa_id"] == group.id
        # 2 lowest points (one per produkt), ordered most-recent first
        assert len(body["dane"]) == 2
        assert body["dane"][0]["platforma"] == "amazon"

    def test_days_query_param_filters_history(
        self,
        client: APIClient,
        group: GrupaProduktow,
        produkty: list[Produkt],
    ) -> None:
        repo = HistoriaCenRepository()
        now = datetime.now(UTC)
        repo.insert_pomiary(
            [
                PomiarCeny(
                    czas=now - timedelta(days=2),
                    produkt_id=produkty[0].id,
                    cena=Decimal("50"),
                ),
                PomiarCeny(
                    czas=now - timedelta(days=10),
                    produkt_id=produkty[0].id,
                    cena=Decimal("80"),
                ),
            ]
        )

        response = client.get(f"/api/groups/{group.id}/prices/?days=5")
        body = response.json()
        assert len(body["dane"]) == 1
        assert body["dane"][0]["najnizsza_cena"] == "50.00"


class TestComparisonAction:
    def test_returns_per_platform_snapshot(
        self,
        client: APIClient,
        group: GrupaProduktow,
        produkty: list[Produkt],  # noqa: ARG002
    ) -> None:
        response = client.get(f"/api/groups/{group.id}/comparison/")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        platforms = {p["platforma"]: p for p in body["platformy"]}
        assert platforms["allegro"]["najnizsza_cena"] == "99.00"
        assert platforms["allegro"]["jest_najlepsza"] is True
        assert platforms["amazon"]["jest_najlepsza"] is False
