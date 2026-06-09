from __future__ import annotations

import logging

from celery import shared_task
from django.db.models import Min

from groups.models import GrupaProduktow
from products.models import Produkt

logger = logging.getLogger(__name__)


@shared_task(name="analytics.tasks.update_product_cache")
def update_product_cache(produkt_id: int) -> None:
    """Refresh per-product analytics cache (avg_30d, std_30d, volatility).

    The heavy stats computation lands in Phase 6; this stub keeps the
    Celery routing wired so callers can already `.delay()` it.
    """
    logger.info("update_product_cache(produkt_id=%s) — stub", produkt_id)


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
