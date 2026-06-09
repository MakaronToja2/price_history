from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from analytics.repositories import HistoriaCenRepository, PomiarCeny
from analytics.services import VolatilityCalculator, interval_minutes_for_volatility

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


class TestVolatilityCalculator:
    def test_returns_default_for_insufficient_data(self) -> None:
        _seed(produkt_id=1, prices=[Decimal("100")] * 4)
        calc = VolatilityCalculator()
        assert calc.calculate(produkt_id=1, now=NOW) == Decimal("0.50")

    def test_zero_for_constant_prices(self) -> None:
        _seed(produkt_id=1, prices=[Decimal("100")] * 10)
        assert VolatilityCalculator().calculate(produkt_id=1, now=NOW) == Decimal("0.00")

    def test_high_for_volatile_prices(self) -> None:
        _seed(
            produkt_id=1,
            prices=[Decimal(p) for p in [100, 150, 50, 200, 60, 180, 70, 160, 90, 140]],
        )
        result = VolatilityCalculator().calculate(produkt_id=1, now=NOW)
        assert result >= Decimal("0.80")

    def test_low_for_stable_prices_with_small_variance(self) -> None:
        # ±2 PLN around 1000 → CV ~ 0.002 → score ~ 0.01
        _seed(
            produkt_id=1,
            prices=[Decimal(p) for p in [1000, 1002, 998, 1001, 999, 1003, 997, 1000]],
        )
        result = VolatilityCalculator().calculate(produkt_id=1, now=NOW)
        assert result < Decimal("0.20")

    def test_capped_at_one(self) -> None:
        _seed(
            produkt_id=1,
            prices=[Decimal(p) for p in [1, 1000, 1, 1000, 1, 1000, 1, 1000, 1, 1000]],
        )
        result = VolatilityCalculator().calculate(produkt_id=1, now=NOW)
        assert result == Decimal("1.00")

    def test_zero_mean_returns_zero(self) -> None:
        _seed(produkt_id=1, prices=[Decimal("0")] * 10)
        assert VolatilityCalculator().calculate(produkt_id=1, now=NOW) == Decimal("0.00")


class TestIntervalMapping:
    @pytest.mark.parametrize(
        ("score", "expected_minutes"),
        [
            (Decimal("0.0"), 1440),
            (Decimal("0.15"), 1440),
            (Decimal("0.2"), 360),
            (Decimal("0.35"), 360),
            (Decimal("0.4"), 120),
            (Decimal("0.55"), 120),
            (Decimal("0.6"), 60),
            (Decimal("0.75"), 60),
            (Decimal("0.8"), 15),
            (Decimal("1.0"), 15),
        ],
    )
    def test_maps_score_to_interval(self, score: Decimal, expected_minutes: int) -> None:
        assert interval_minutes_for_volatility(score) == expected_minutes
