from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from analytics.repositories import HistoriaCenRepository, PomiarCeny

pytestmark = pytest.mark.django_db(databases=["timeseries"])


@pytest.fixture
def repo() -> HistoriaCenRepository:
    return HistoriaCenRepository()


@pytest.fixture(autouse=True)
def _clean(repo: HistoriaCenRepository) -> None:
    repo.truncate()


def _ts(hours_ago: int = 0) -> datetime:
    return datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC) - timedelta(hours=hours_ago)


class TestInsertBatch:
    def test_inserts_marks_lowest(self, repo: HistoriaCenRepository) -> None:
        czas = _ts()
        repo.insert_pomiary(
            [
                PomiarCeny(czas, produkt_id=1, sprzedawca_id=10, cena=Decimal("100.00")),
                PomiarCeny(czas, produkt_id=1, sprzedawca_id=11, cena=Decimal("90.00")),
                PomiarCeny(czas, produkt_id=1, sprzedawca_id=12, cena=Decimal("110.00")),
            ]
        )

        rows = repo.get_pomiary_for_produkt(produkt_id=1)
        assert len(rows) == 3
        lowest = [r for r in rows if r["jest_najnizsza"]]
        assert len(lowest) == 1
        assert lowest[0]["sprzedawca_id"] == 11
        assert lowest[0]["cena"] == Decimal("90.00")

    def test_groups_by_product(self, repo: HistoriaCenRepository) -> None:
        czas = _ts()
        repo.insert_pomiary(
            [
                PomiarCeny(czas, produkt_id=1, sprzedawca_id=10, cena=Decimal("50")),
                PomiarCeny(czas, produkt_id=2, sprzedawca_id=10, cena=Decimal("200")),
                PomiarCeny(czas, produkt_id=2, sprzedawca_id=11, cena=Decimal("180")),
            ]
        )

        p1 = [r for r in repo.get_pomiary_for_produkt(produkt_id=1) if r["jest_najnizsza"]]
        p2 = [r for r in repo.get_pomiary_for_produkt(produkt_id=2) if r["jest_najnizsza"]]

        assert p1[0]["cena"] == Decimal("50")
        assert p2[0]["cena"] == Decimal("180")

    def test_empty_batch_is_noop(self, repo: HistoriaCenRepository) -> None:
        repo.insert_pomiary([])
        assert repo.get_pomiary_for_produkt(produkt_id=1) == []


class TestLowestPriceHistory:
    def test_returns_only_lowest_ordered_desc(self, repo: HistoriaCenRepository) -> None:
        repo.insert_pomiary(
            [
                PomiarCeny(_ts(2), produkt_id=1, sprzedawca_id=10, cena=Decimal("100")),
                PomiarCeny(_ts(2), produkt_id=1, sprzedawca_id=11, cena=Decimal("95")),
                PomiarCeny(_ts(1), produkt_id=1, sprzedawca_id=10, cena=Decimal("90")),
                PomiarCeny(_ts(1), produkt_id=1, sprzedawca_id=11, cena=Decimal("92")),
            ]
        )

        history = repo.get_lowest_history(produkt_id=1, since=_ts(24))
        assert [r["cena"] for r in history] == [Decimal("90"), Decimal("95")]


class TestStats:
    def test_computes_avg_stddev_min_max_count(self, repo: HistoriaCenRepository) -> None:
        # Three lowest-price snapshots: 100, 110, 120
        for offset, cena in enumerate([100, 110, 120]):
            repo.insert_pomiary(
                [
                    PomiarCeny(_ts(offset), produkt_id=1, sprzedawca_id=10, cena=Decimal(cena)),
                    PomiarCeny(
                        _ts(offset),
                        produkt_id=1,
                        sprzedawca_id=11,
                        cena=Decimal(cena + 50),
                    ),
                ]
            )

        stats = repo.get_stats(produkt_id=1, since=_ts(72))
        assert stats["count"] == 3
        assert stats["min"] == Decimal("100")
        assert stats["max"] == Decimal("120")
        assert stats["avg"] == pytest.approx(Decimal("110"), abs=Decimal("0.01"))
        assert stats["stddev"] == pytest.approx(Decimal("10"), abs=Decimal("0.5"))

    def test_stats_for_empty_returns_zero_count(self, repo: HistoriaCenRepository) -> None:
        stats = repo.get_stats(produkt_id=999, since=_ts(72))
        assert stats["count"] == 0
        assert stats["avg"] is None
        assert stats["stddev"] is None
