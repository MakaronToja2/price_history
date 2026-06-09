from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from analytics.repositories import HistoriaCenRepository
from groups.models import GrupaProduktow
from products.models import Produkt
from scrapers.base import OfertaZewnetrzna, ProduktInfo, WynikScrapowania
from users.models import User

pytestmark = pytest.mark.django_db(databases=["default", "timeseries"])


@pytest.fixture(autouse=True)
def _truncate_timeseries() -> None:
    HistoriaCenRepository().truncate()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(email="o@example.com", password="Pass1234!")


@pytest.fixture
def grupa(user: User) -> GrupaProduktow:
    return GrupaProduktow.objects.create(uzytkownik=user, nazwa="RTX 4080")


@pytest.fixture
def client(user: User) -> APIClient:
    api = APIClient()
    refresh = RefreshToken.for_user(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api


@pytest.fixture
def fake_scrape() -> WynikScrapowania:
    return WynikScrapowania(
        produkt=ProduktInfo(nazwa="Karta"),
        oferty=[
            OfertaZewnetrzna(
                sprzedawca_zewnetrzny_id="S1",
                sprzedawca_nazwa="Sklep",
                cena=Decimal("2399.00"),
            )
        ],
    )


def _url(group_id: int) -> str:
    return f"/api/groups/{group_id}/products/"


class TestAddProduct:
    def test_creates_product_from_allegro_url(
        self, client: APIClient, grupa: GrupaProduktow, fake_scrape: WynikScrapowania
    ) -> None:
        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            response = client.post(
                _url(grupa.id),
                {"url": "https://allegro.pl/oferta/karta-12345678"},
                format="json",
            )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["platforma"] == "allegro"
        assert body["zewnetrzny_id"] == "12345678"
        assert body["task_id"]
        assert Produkt.objects.filter(grupa=grupa, zewnetrzny_id="12345678").exists()

    def test_creates_product_from_amazon_url(
        self, client: APIClient, grupa: GrupaProduktow
    ) -> None:
        # Amazon scraper raises NotImplementedError; capture it so we can
        # still observe the row was created before the queued task ran.
        with patch("scrapers.tasks.fetch_product_price.apply_async") as mock_apply:
            mock_apply.return_value.id = "fake-task-id"
            # Use .delay equivalence: rebind
            response = client.post(
                _url(grupa.id),
                {"url": "https://amazon.pl/dp/B08N5WRWNW"},
                format="json",
            )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["platforma"] == "amazon"
        assert body["zewnetrzny_id"] == "B08N5WRWNW"

    def test_rejects_invalid_url(self, client: APIClient, grupa: GrupaProduktow) -> None:
        response = client.post(
            _url(grupa.id),
            {"url": "https://ebay.com/itm/12345"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_duplicate(
        self, client: APIClient, grupa: GrupaProduktow, fake_scrape: WynikScrapowania
    ) -> None:
        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            client.post(
                _url(grupa.id),
                {"url": "https://allegro.pl/oferta/karta-12345678"},
                format="json",
            )

        response = client.post(
            _url(grupa.id),
            {"url": "https://allegro.pl/oferta/karta-12345678"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_other_users_group_returns_404(
        self,
        client: APIClient,
    ) -> None:
        other = User.objects.create_user(email="x@y.com", password="Pass1234!")
        foreign = GrupaProduktow.objects.create(uzytkownik=other, nazwa="Foreign")
        response = client.post(
            _url(foreign.id),
            {"url": "https://allegro.pl/oferta/12345678"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Produkt.objects.filter(grupa=foreign).exists()

    def test_requires_auth(self, grupa: GrupaProduktow) -> None:
        anon = APIClient()
        response = anon.post(
            _url(grupa.id),
            {"url": "https://allegro.pl/oferta/12345678"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListProducts:
    def test_returns_products_in_group(
        self, client: APIClient, grupa: GrupaProduktow, fake_scrape: WynikScrapowania
    ) -> None:
        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            client.post(
                _url(grupa.id),
                {"url": "https://allegro.pl/oferta/12345678"},
                format="json",
            )

        response = client.get(_url(grupa.id))
        assert response.status_code == status.HTTP_200_OK
        items = response.json()
        assert len(items) == 1
        assert items[0]["zewnetrzny_id"] == "12345678"
