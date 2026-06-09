from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from analytics.repositories import HistoriaCenRepository, PomiarCeny
from analytics.tasks import update_product_cache
from groups.models import GrupaProduktow
from products.models import Platforma, Produkt
from users.models import User

pytestmark = pytest.mark.django_db(databases=["default", "timeseries"])


@pytest.fixture(autouse=True)
def _clean() -> None:
    HistoriaCenRepository().truncate()


@pytest.fixture
def produkt() -> Produkt:
    user = User.objects.create_user(email="a@b.com", password="Pass1234!")
    grupa = GrupaProduktow.objects.create(uzytkownik=user, nazwa="G")
    return Produkt.objects.create(
        grupa=grupa,
        platforma=Platforma.objects.get(nazwa="allegro"),
        zewnetrzny_id="P",
        url="https://allegro.pl/oferta/123",
        aktualna_najnizsza_cena=Decimal("100.00"),
    )


def _seed_recent(produkt_id: int, prices: list[Decimal]) -> None:
    """Seed prices in the last 20 days so the 30-day window catches them
    regardless of when the test runs."""
    repo = HistoriaCenRepository()
    now = datetime.now(UTC)
    pomiary = [
        PomiarCeny(czas=now - timedelta(days=i), produkt_id=produkt_id, cena=p)
        for i, p in enumerate(prices)
    ]
    repo.insert_pomiary(pomiary)


class TestUpdateProductCache:
    def test_writes_avg_and_stddev_from_30d_window(self, produkt: Produkt) -> None:
        _seed_recent(produkt.id, [Decimal(p) for p in [100, 110, 90, 105, 95, 100]])

        update_product_cache(produkt.id)
        produkt.refresh_from_db()

        assert produkt.srednia_cena_30d is not None
        assert Decimal("99") < produkt.srednia_cena_30d < Decimal("101")
        assert produkt.odchylenie_std_30d is not None
        assert produkt.odchylenie_std_30d > Decimal("0")

    def test_writes_volatility_and_interval(self, produkt: Produkt) -> None:
        # Constant prices → CV 0 → score 0 → interval 1440
        _seed_recent(produkt.id, [Decimal("100")] * 10)

        update_product_cache(produkt.id)
        produkt.refresh_from_db()

        assert produkt.wskaznik_zmiennosci == Decimal("0.00")
        assert produkt.interwal_sprawdzania_min == 1440

    def test_volatile_prices_increase_polling_frequency(self, produkt: Produkt) -> None:
        _seed_recent(
            produkt.id,
            [Decimal(p) for p in [100, 200, 50, 250, 60, 240, 70, 230, 80, 220]],
        )

        update_product_cache(produkt.id)
        produkt.refresh_from_db()

        assert produkt.wskaznik_zmiennosci >= Decimal("0.80")
        assert produkt.interwal_sprawdzania_min == 15

    def test_nastepne_sprawdzenie_is_set(self, produkt: Produkt) -> None:
        _seed_recent(produkt.id, [Decimal("100")] * 10)
        before = datetime.now(UTC)
        update_product_cache(produkt.id)
        produkt.refresh_from_db()
        assert produkt.nastepne_sprawdzenie is not None
        assert produkt.nastepne_sprawdzenie > before

    def test_missing_produkt_is_noop(self) -> None:
        # No exception even if produkt does not exist
        update_product_cache(999_999)
