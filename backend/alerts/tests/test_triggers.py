from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.core import mail

from alerts.models import Alert
from analytics.repositories import HistoriaCenRepository, PomiarCeny
from analytics.tasks import update_product_cache
from groups.models import GrupaProduktow
from products.models import Platforma, Produkt
from users.models import User

pytestmark = pytest.mark.django_db(databases=["default", "timeseries"])


@pytest.fixture(autouse=True)
def _clean() -> None:
    HistoriaCenRepository().truncate()
    mail.outbox.clear()


def _make_produkt(
    *, najnizsza: Decimal | None = Decimal("100.00"), srednia: Decimal | None = None
) -> Produkt:
    user = User.objects.create_user(email="t@x.com", password="Pass1234!")
    grupa = GrupaProduktow.objects.create(
        uzytkownik=user,
        nazwa="Grupa",
        najnizsza_cena_globalna=najnizsza,
        najlepsza_platforma="allegro",
        najlepszy_sprzedawca="Sklep",
    )
    return Produkt.objects.create(
        grupa=grupa,
        platforma=Platforma.objects.get(nazwa="allegro"),
        zewnetrzny_id="P",
        url="https://allegro.pl/oferta/123",
        aktualna_najnizsza_cena=najnizsza,
        aktualny_najlepszy_sprzedawca="Sklep",
        srednia_cena_30d=srednia,
    )


def _seed_recent(produkt_id: int, prices: list[Decimal]) -> None:
    repo = HistoriaCenRepository()
    now = datetime.now(UTC)
    pomiary = [
        PomiarCeny(czas=now - timedelta(days=i), produkt_id=produkt_id, cena=p)
        for i, p in enumerate(prices)
    ]
    repo.insert_pomiary(pomiary)


class TestDocelowyAlert:
    def test_sends_email_when_price_at_or_below_threshold(self) -> None:
        produkt = _make_produkt(najnizsza=Decimal("90.00"))
        Alert.objects.create(
            grupa=produkt.grupa,
            typ_alertu=Alert.TYP_DOCELOWY,
            prog_ceny=Decimal("100.00"),
        )
        _seed_recent(produkt.id, [Decimal("90.00")] * 10)

        update_product_cache(produkt.id)
        assert len(mail.outbox) == 1
        assert "90.00" in mail.outbox[0].body
        assert produkt.grupa.uzytkownik.email in mail.outbox[0].to

    def test_no_email_when_price_above_threshold(self) -> None:
        produkt = _make_produkt(najnizsza=Decimal("150.00"))
        Alert.objects.create(
            grupa=produkt.grupa,
            typ_alertu=Alert.TYP_DOCELOWY,
            prog_ceny=Decimal("100.00"),
        )
        _seed_recent(produkt.id, [Decimal("150.00")] * 10)

        update_product_cache(produkt.id)
        assert len(mail.outbox) == 0

    def test_inactive_alert_does_not_fire(self) -> None:
        produkt = _make_produkt(najnizsza=Decimal("80.00"))
        Alert.objects.create(
            grupa=produkt.grupa,
            typ_alertu=Alert.TYP_DOCELOWY,
            prog_ceny=Decimal("100.00"),
            aktywny=False,
        )
        _seed_recent(produkt.id, [Decimal("80.00")] * 10)

        update_product_cache(produkt.id)
        assert len(mail.outbox) == 0


class TestSpadekCenyAlert:
    def test_fires_on_large_percent_drop(self) -> None:
        # srednia_30d will be ~100, najnizsza is 70 → 30% drop
        produkt = _make_produkt(najnizsza=Decimal("70.00"), srednia=Decimal("100.00"))
        Alert.objects.create(
            grupa=produkt.grupa,
            typ_alertu=Alert.TYP_SPADEK_CENY,
            prog_procent=Decimal("10.0"),
        )
        _seed_recent(produkt.id, [Decimal("100.00")] * 10)

        update_product_cache(produkt.id)
        assert len(mail.outbox) == 1

    def test_no_fire_on_small_drop(self) -> None:
        produkt = _make_produkt(najnizsza=Decimal("95.00"), srednia=Decimal("100.00"))
        Alert.objects.create(
            grupa=produkt.grupa,
            typ_alertu=Alert.TYP_SPADEK_CENY,
            prog_procent=Decimal("10.0"),
        )
        _seed_recent(produkt.id, [Decimal("100.00")] * 10)

        update_product_cache(produkt.id)
        assert len(mail.outbox) == 0


class TestFlashSaleAlert:
    def test_fires_on_anomaly(self) -> None:
        produkt = _make_produkt(najnizsza=Decimal("70.00"))
        Alert.objects.create(grupa=produkt.grupa, typ_alertu=Alert.TYP_FLASH_SALE)
        # Stable 100±2 → std ~1.8; 70 PLN is many sigmas below
        _seed_recent(
            produkt.id,
            [Decimal(p) for p in [100, 102, 98, 101, 99, 100, 103, 97, 100, 102, 98, 100]],
        )

        update_product_cache(produkt.id)
        assert len(mail.outbox) == 1

    def test_no_fire_without_anomaly(self) -> None:
        produkt = _make_produkt(najnizsza=Decimal("99.00"))
        Alert.objects.create(grupa=produkt.grupa, typ_alertu=Alert.TYP_FLASH_SALE)
        _seed_recent(
            produkt.id,
            [Decimal(p) for p in [100, 102, 98, 101, 99, 100, 103, 97, 100, 102, 98, 100]],
        )

        update_product_cache(produkt.id)
        assert len(mail.outbox) == 0


class TestOstatnieWyzwolenieStamped:
    def test_alert_records_last_trigger(self) -> None:
        produkt = _make_produkt(najnizsza=Decimal("90.00"))
        alert = Alert.objects.create(
            grupa=produkt.grupa,
            typ_alertu=Alert.TYP_DOCELOWY,
            prog_ceny=Decimal("100.00"),
        )
        _seed_recent(produkt.id, [Decimal("90.00")] * 10)
        update_product_cache(produkt.id)

        alert.refresh_from_db()
        assert alert.ostatnie_wyzwolenie is not None
