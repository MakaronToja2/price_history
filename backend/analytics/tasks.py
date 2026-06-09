from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from celery import shared_task
from django.db.models import Min

from groups.models import GrupaProduktow
from products.models import Produkt

from .repositories import HistoriaCenRepository
from .services import (
    VOLATILITY_WINDOW_DAYS,
    AnomalyDetector,
    VolatilityCalculator,
    interval_minutes_for_volatility,
)

logger = logging.getLogger(__name__)


@shared_task(name="analytics.tasks.update_product_cache")
def update_product_cache(produkt_id: int) -> None:
    """Refresh per-product analytics cache.

    Computes the 30-day mean and stddev of the lowest prices, the
    coefficient-of-variation-based volatility score, and from that the
    smart-polling cadence (nastepne_sprawdzenie). Then runs anomaly
    detection on the current price and logs hits for Phase 7 alerting
    to pick up.
    """
    try:
        produkt = Produkt.objects.get(id=produkt_id)
    except Produkt.DoesNotExist:
        return

    now = datetime.now(UTC)
    repo = HistoriaCenRepository()
    stats = repo.get_stats(
        produkt_id=produkt.id,
        since=now - timedelta(days=VOLATILITY_WINDOW_DAYS),
    )

    if stats["count"] > 0:
        produkt.srednia_cena_30d = (
            Decimal(str(stats["avg"])).quantize(Decimal("0.01"))
            if stats["avg"] is not None
            else None
        )
        produkt.odchylenie_std_30d = (
            Decimal(str(stats["stddev"])).quantize(Decimal("0.01"))
            if stats["stddev"] is not None
            else None
        )

    score = VolatilityCalculator(repo).calculate(produkt_id=produkt.id, now=now)
    produkt.wskaznik_zmiennosci = score
    produkt.interwal_sprawdzania_min = interval_minutes_for_volatility(score)
    produkt.nastepne_sprawdzenie = now + timedelta(minutes=produkt.interwal_sprawdzania_min)

    produkt.save(
        update_fields=[
            "srednia_cena_30d",
            "odchylenie_std_30d",
            "wskaznik_zmiennosci",
            "interwal_sprawdzania_min",
            "nastepne_sprawdzenie",
        ]
    )

    if produkt.aktualna_najnizsza_cena is not None:
        anomaly = AnomalyDetector(repo).check(
            produkt_id=produkt.id,
            aktualna_cena=produkt.aktualna_najnizsza_cena,
            now=now,
        )
        if anomaly.is_anomaly:
            logger.info(
                "Anomaly detected for produkt %s: z=%s, spadek=%s%%",
                produkt.id,
                anomaly.z_score,
                anomaly.spadek_procent,
            )
        _evaluate_alerts(produkt, anomaly_detected=anomaly.is_anomaly)


def _evaluate_alerts(produkt: Produkt, *, anomaly_detected: bool) -> None:
    """Trigger any active alerts on the produkt's grupa.

    Checks the grupa's cross-platform best price (najnizsza_cena_globalna)
    against each alert's threshold and enqueues an email when matched.
    """
    from alerts.models import Alert
    from alerts.tasks import send_alert_email

    grupa = produkt.grupa
    cena = grupa.najnizsza_cena_globalna
    if cena is None:
        return

    alerty = Alert.objects.filter(grupa=grupa, aktywny=True)
    for alert in alerty:
        matched = False

        if alert.typ_alertu == Alert.TYP_DOCELOWY:
            matched = alert.prog_ceny is not None and cena <= alert.prog_ceny

        elif alert.typ_alertu == Alert.TYP_SPADEK_CENY:
            if alert.prog_procent is None or produkt.srednia_cena_30d is None:
                continue
            srednia = produkt.srednia_cena_30d
            if srednia > 0:
                spadek = (srednia - cena) / srednia * Decimal("100")
                matched = spadek >= alert.prog_procent

        elif alert.typ_alertu == Alert.TYP_FLASH_SALE:
            matched = anomaly_detected

        if matched:
            send_alert_email.delay(
                alert.id,
                str(cena),
                grupa.najlepsza_platforma,
                grupa.najlepszy_sprzedawca,
            )


@shared_task(name="analytics.tasks.update_group_cache")
def update_group_cache(grupa_id: int) -> None:
    """Recompute cross-platform best price for a group.

    `najnizsza_cena_globalna` is the minimum of each product's
    `aktualna_najnizsza_cena` across all platforms in the group. The
    best-seller fields are copied from the winning product.
    """
    grupa = GrupaProduktow.objects.filter(id=grupa_id).first()
    if grupa is None:
        return

    agg = grupa.produkty.exclude(aktualna_najnizsza_cena__isnull=True).aggregate(
        min_cena=Min("aktualna_najnizsza_cena")
    )
    min_cena = agg["min_cena"]

    if min_cena is None:
        grupa.najnizsza_cena_globalna = None
        grupa.najlepsza_platforma = ""
        grupa.najlepszy_sprzedawca = ""
    else:
        winner: Produkt | None = (
            grupa.produkty.select_related("platforma")
            .filter(aktualna_najnizsza_cena=min_cena)
            .order_by("id")
            .first()
        )
        grupa.najnizsza_cena_globalna = min_cena
        grupa.najlepsza_platforma = winner.platforma.nazwa if winner else ""
        grupa.najlepszy_sprzedawca = winner.aktualny_najlepszy_sprzedawca if winner else ""

    grupa.save(
        update_fields=[
            "najnizsza_cena_globalna",
            "najlepsza_platforma",
            "najlepszy_sprzedawca",
        ]
    )
