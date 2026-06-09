from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from groups.models import GrupaProduktow
from products.models import Platforma, Produkt
from scrapers.tasks import enqueue_due_fetches
from users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def grupa() -> GrupaProduktow:
    user = User.objects.create_user(email="beat@x.com", password="Pass1234!")
    return GrupaProduktow.objects.create(uzytkownik=user, nazwa="G")


def _make(grupa: GrupaProduktow, **overrides: object) -> Produkt:
    defaults = {
        "grupa": grupa,
        "platforma": Platforma.objects.get(nazwa="allegro"),
        "zewnetrzny_id": "P",
        "url": "https://allegro.pl/oferta/123",
        "aktywny": True,
    }
    defaults.update(overrides)
    return Produkt.objects.create(**defaults)


class TestEnqueueDueFetches:
    def test_enqueues_overdue_active_products(self, grupa: GrupaProduktow) -> None:
        past = datetime.now(UTC) - timedelta(minutes=5)
        future = datetime.now(UTC) + timedelta(minutes=30)

        due_a = _make(grupa, zewnetrzny_id="A", nastepne_sprawdzenie=past)
        due_b = _make(grupa, zewnetrzny_id="B", nastepne_sprawdzenie=past)
        _make(grupa, zewnetrzny_id="C", nastepne_sprawdzenie=future)

        with patch("scrapers.tasks.fetch_product_price.delay") as mock_delay:
            count = enqueue_due_fetches()

        assert count == 2
        ids = {call.args[0] for call in mock_delay.call_args_list}
        assert ids == {due_a.id, due_b.id}

    def test_skips_inactive_products(self, grupa: GrupaProduktow) -> None:
        past = datetime.now(UTC) - timedelta(minutes=5)
        _make(grupa, zewnetrzny_id="A", nastepne_sprawdzenie=past, aktywny=False)

        with patch("scrapers.tasks.fetch_product_price.delay") as mock_delay:
            count = enqueue_due_fetches()

        assert count == 0
        assert mock_delay.call_count == 0

    def test_handles_products_with_null_nastepne_sprawdzenie(self, grupa: GrupaProduktow) -> None:
        # Brand-new produkt (never fetched): nastepne_sprawdzenie is NULL.
        # Postgres NULL never matches `<= now`, so it's NOT enqueued by this
        # task — fetch_product_price runs once on creation via the add-product
        # endpoint, which then sets nastepne_sprawdzenie.
        _make(grupa, zewnetrzny_id="A", nastepne_sprawdzenie=None)

        with patch("scrapers.tasks.fetch_product_price.delay") as mock_delay:
            count = enqueue_due_fetches()

        assert count == 0
        assert mock_delay.call_count == 0


def test_beat_schedule_includes_enqueue_due_fetches() -> None:
    from config import celery_app

    assert "enqueue-due-fetches" in celery_app.conf.beat_schedule
    entry = celery_app.conf.beat_schedule["enqueue-due-fetches"]
    assert entry["task"] == "scrapers.tasks.enqueue_due_fetches"
