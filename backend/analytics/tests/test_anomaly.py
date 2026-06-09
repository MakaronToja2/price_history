from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from analytics.repositories import HistoriaCenRepository, PomiarCeny
from analytics.services import AnomalyDetector

pytestmark = pytest.mark.django_db(databases=["timeseries"])


@pytest.fixture(autouse=True)
def _clean() -> None:
    HistoriaCenRepository().truncate()


NOW = datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)


def _seed(produkt_id: int, prices: list[Decimal]) -> None:
    repo = HistoriaCenRepository()
    pomiary = [
        PomiarCeny(czas=NOW - timedelta(days=i), produkt_id=produkt_id, cena=p)
        for i, p in enumerate(prices)
    ]
    repo.insert_pomiary(pomiary)


class TestAnomalyDetector:
    def test_insufficient_data_returns_not_anomaly(self) -> None:
        _seed(produkt_id=1, prices=[Decimal("100")] * 5)
        result = AnomalyDetector().check(produkt_id=1, aktualna_cena=Decimal("50"), now=NOW)
        assert not result.is_anomaly
        assert result.reason == "insufficient_data"

    def test_zero_stddev_returns_not_anomaly(self) -> None:
        _seed(produkt_id=1, prices=[Decimal("100")] * 15)
        result = AnomalyDetector().check(produkt_id=1, aktualna_cena=Decimal("80"), now=NOW)
        assert not result.is_anomaly
        assert result.reason == "no_price_variation"

    def test_large_drop_flagged_as_anomaly(self) -> None:
        # Mean ~100, std ~5, 80 PLN = (80-100)/5 = -4 sigma
        _seed(
            produkt_id=1,
            prices=[Decimal(p) for p in [100, 102, 98, 101, 99, 100, 103, 97, 100, 102, 98, 100]],
        )
        result = AnomalyDetector().check(produkt_id=1, aktualna_cena=Decimal("80"), now=NOW)
        assert result.is_anomaly
        assert result.z_score is not None
        assert result.z_score < Decimal("-2")
        assert result.srednia_okolic is not None
        assert result.spadek_procent is not None
        assert result.spadek_procent < Decimal("-15")

    def test_small_drop_not_anomaly(self) -> None:
        _seed(
            produkt_id=1,
            prices=[Decimal(p) for p in [100, 102, 98, 101, 99, 100, 103, 97, 100, 102, 98, 100]],
        )
        # 99 is well within 1σ of the ~100 mean (std ≈ 1.8)
        result = AnomalyDetector().check(produkt_id=1, aktualna_cena=Decimal("99"), now=NOW)
        assert not result.is_anomaly

    def test_price_increase_not_flagged(self) -> None:
        _seed(
            produkt_id=1,
            prices=[Decimal(p) for p in [100, 102, 98, 101, 99, 100, 103, 97, 100, 102, 98, 100]],
        )
        result = AnomalyDetector().check(produkt_id=1, aktualna_cena=Decimal("200"), now=NOW)
        assert not result.is_anomaly
