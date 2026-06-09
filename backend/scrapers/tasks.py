from __future__ import annotations

import logging
from datetime import UTC, datetime

import requests
from celery import shared_task
from django.db import transaction

from analytics.repositories import HistoriaCenRepository, PomiarCeny
from analytics.tasks import update_group_cache, update_product_cache
from products.models import Produkt

from .allegro import AllegroClient, AllegroError
from .amazon import AmazonScraper
from .base import WynikScrapowania

logger = logging.getLogger(__name__)


@shared_task(
    name="scrapers.tasks.fetch_product_price",
    autoretry_for=(requests.RequestException, AllegroError, TimeoutError),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def fetch_product_price(produkt_id: int) -> None:
    """Fetch current prices for a single produkt and persist them.

    Steps:
      1. Resolve the scraper for the product's platforma.
      2. Call `scraper.pobierz(...)` and receive `WynikScrapowania`.
      3. Insert one HistoriaCen row per offer (lowest is flagged automatically).
      4. Update Produkt cache fields (aktualna_*) in the transactional DB.
      5. Enqueue update_product_cache + update_group_cache.

    Routed to: wysoki_priorytet
    """
    try:
        produkt = Produkt.objects.select_related("platforma", "grupa").get(id=produkt_id)
    except Produkt.DoesNotExist:
        logger.warning("fetch_product_price: produkt %s not found", produkt_id)
        return

    wynik = _scrape_for(produkt)
    if not wynik.oferty:
        _stamp_check_time(produkt)
        logger.info("fetch_product_price: no offers for produkt %s", produkt_id)
        return

    czas = datetime.now(UTC)
    pomiary = [
        PomiarCeny(
            czas=czas,
            produkt_id=produkt.id,
            sprzedawca_id=None,
            cena=o.cena,
            waluta=o.waluta,
        )
        for o in wynik.oferty
    ]
    HistoriaCenRepository().insert_pomiary(pomiary)

    najtansza = min(wynik.oferty, key=lambda o: o.cena)

    with transaction.atomic():
        produkt.nazwa = wynik.produkt.nazwa or produkt.nazwa
        produkt.url_obrazka = wynik.produkt.url_obrazka or produkt.url_obrazka
        produkt.aktualna_najnizsza_cena = najtansza.cena
        produkt.aktualny_najlepszy_sprzedawca = najtansza.sprzedawca_nazwa
        produkt.liczba_sprzedawcow = len(wynik.oferty)
        produkt.ostatnie_sprawdzenie = czas
        produkt.save(
            update_fields=[
                "nazwa",
                "url_obrazka",
                "aktualna_najnizsza_cena",
                "aktualny_najlepszy_sprzedawca",
                "liczba_sprzedawcow",
                "ostatnie_sprawdzenie",
            ]
        )

    # Run group cache first so update_product_cache (which evaluates alerts
    # against grupa.najnizsza_cena_globalna) sees the current aggregate.
    update_group_cache(produkt.grupa_id)
    update_product_cache.delay(produkt.id)


@shared_task(name="scrapers.tasks.enqueue_due_fetches")
def enqueue_due_fetches() -> int:
    """Beat-scheduled scanner: enqueue fetch_product_price for every
    active produkt whose nastepne_sprawdzenie is in the past.

    `nastepne_sprawdzenie` is set by update_product_cache based on the
    smart-polling cadence derived from wskaznik_zmiennosci, so one
    periodic sweep automatically respects per-product polling intervals.

    Routed to: wysoki_priorytet (Beat options.queue override).

    Returns:
        Number of products enqueued (for logging/metrics).
    """
    now = datetime.now(UTC)
    due_qs = Produkt.objects.filter(
        aktywny=True,
        nastepne_sprawdzenie__lte=now,
    ).values_list("id", flat=True)

    count = 0
    for produkt_id in due_qs:
        fetch_product_price.delay(produkt_id)
        count += 1
    logger.info("enqueue_due_fetches: queued %s product(s)", count)
    return count


def _scrape_for(produkt: Produkt) -> WynikScrapowania:
    nazwa_platformy = produkt.platforma.nazwa
    if nazwa_platformy == "allegro":
        return AllegroClient().pobierz(produkt.zewnetrzny_id, "product")
    if nazwa_platformy == "amazon":
        return AmazonScraper().pobierz(produkt.zewnetrzny_id, "asin")
    raise ValueError(f"Unsupported platforma: {nazwa_platformy!r}")


def _stamp_check_time(produkt: Produkt) -> None:
    produkt.ostatnie_sprawdzenie = datetime.now(UTC)
    produkt.save(update_fields=["ostatnie_sprawdzenie"])
