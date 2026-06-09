from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from analytics.repositories import HistoriaCenRepository
from groups.models import GrupaProduktow
from products.models import Platforma, Produkt
from scrapers.base import OfertaZewnetrzna, ProduktInfo, WynikScrapowania
from scrapers.tasks import fetch_product_price
from users.models import User

pytestmark = pytest.mark.django_db(databases=["default", "timeseries"])


@pytest.fixture(autouse=True)
def _truncate_timeseries() -> None:
    HistoriaCenRepository().truncate()


@pytest.fixture
def user() -> User:
    return User.objects.create_user(email="o@example.com", password="Pass1234!")


@pytest.fixture
def grupa(user: User) -> GrupaProduktow:
    return GrupaProduktow.objects.create(uzytkownik=user, nazwa="RTX 4080")


@pytest.fixture
def produkt(grupa: GrupaProduktow) -> Produkt:
    allegro = Platforma.objects.get(nazwa="allegro")
    return Produkt.objects.create(
        grupa=grupa,
        platforma=allegro,
        zewnetrzny_id="P-12345",
        url="https://allegro.pl/produkt/foo-P-12345",
    )


@pytest.fixture
def fake_scrape() -> WynikScrapowania:
    return WynikScrapowania(
        produkt=ProduktInfo(nazwa="Karta RTX 4080", url_obrazka="https://cdn/img.jpg"),
        oferty=[
            OfertaZewnetrzna(
                sprzedawca_zewnetrzny_id="S1",
                sprzedawca_nazwa="SuperSklep",
                cena=Decimal("2499.00"),
            ),
            OfertaZewnetrzna(
                sprzedawca_zewnetrzny_id="S2",
                sprzedawca_nazwa="TaniSprzet",
                cena=Decimal("2599.00"),
            ),
            OfertaZewnetrzna(
                sprzedawca_zewnetrzny_id="S3",
                sprzedawca_nazwa="MegaShop",
                cena=Decimal("2399.00"),
            ),
        ],
    )


class TestFetchProductPrice:
    def test_writes_historia_cen_with_lowest_flag(
        self, produkt: Produkt, fake_scrape: WynikScrapowania
    ) -> None:
        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            fetch_product_price(produkt.id)

        rows = HistoriaCenRepository().get_pomiary_for_produkt(produkt_id=produkt.id)
        assert len(rows) == 3
        lowest = [r for r in rows if r["jest_najnizsza"]]
        assert len(lowest) == 1
        assert lowest[0]["cena"] == Decimal("2399.00")

    def test_updates_produkt_cache(self, produkt: Produkt, fake_scrape: WynikScrapowania) -> None:
        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            fetch_product_price(produkt.id)

        produkt.refresh_from_db()
        assert produkt.aktualna_najnizsza_cena == Decimal("2399.00")
        assert produkt.aktualny_najlepszy_sprzedawca == "MegaShop"
        assert produkt.liczba_sprzedawcow == 3
        assert produkt.nazwa == "Karta RTX 4080"
        assert produkt.url_obrazka == "https://cdn/img.jpg"
        assert produkt.ostatnie_sprawdzenie is not None

    def test_updates_grupa_cache(self, produkt: Produkt, fake_scrape: WynikScrapowania) -> None:
        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            fetch_product_price(produkt.id)

        grupa = produkt.grupa
        grupa.refresh_from_db()
        assert grupa.najnizsza_cena_globalna == Decimal("2399.00")
        assert grupa.najlepsza_platforma == "allegro"
        assert grupa.najlepszy_sprzedawca == "MegaShop"

    def test_multiple_products_keep_group_minimum(
        self, produkt: Produkt, fake_scrape: WynikScrapowania
    ) -> None:
        # Add a second product (amazon) with a higher minimum price so the
        # group's cross-platform minimum stays on allegro.
        amazon = Platforma.objects.get(nazwa="amazon")
        produkt2 = Produkt.objects.create(
            grupa=produkt.grupa,
            platforma=amazon,
            zewnetrzny_id="ASIN1234",
            url="https://amazon.pl/dp/ASIN1234",
            aktualna_najnizsza_cena=Decimal("2700.00"),
            aktualny_najlepszy_sprzedawca="AmazonSeller",
        )

        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            fetch_product_price(produkt.id)

        produkt.grupa.refresh_from_db()
        assert produkt.grupa.najnizsza_cena_globalna == Decimal("2399.00")
        assert produkt.grupa.najlepsza_platforma == "allegro"
        # Sanity check second product is untouched
        produkt2.refresh_from_db()
        assert produkt2.aktualna_najnizsza_cena == Decimal("2700.00")

    def test_uses_current_timestamp(self, produkt: Produkt, fake_scrape: WynikScrapowania) -> None:
        before = datetime.now(UTC)
        with patch("scrapers.tasks._scrape_for", return_value=fake_scrape):
            fetch_product_price(produkt.id)
        after = datetime.now(UTC)

        rows = HistoriaCenRepository().get_pomiary_for_produkt(produkt_id=produkt.id)
        for row in rows:
            assert before <= row["czas"] <= after

    def test_no_offers_skips_writes(self, produkt: Produkt) -> None:
        empty = WynikScrapowania(produkt=ProduktInfo(nazwa="Karta"), oferty=[])
        with patch("scrapers.tasks._scrape_for", return_value=empty):
            fetch_product_price(produkt.id)

        rows = HistoriaCenRepository().get_pomiary_for_produkt(produkt_id=produkt.id)
        assert rows == []
        produkt.refresh_from_db()
        assert produkt.aktualna_najnizsza_cena is None
