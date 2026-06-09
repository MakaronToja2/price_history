from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd

from .repositories import HistoriaCenRepository

DEFAULT_VOLATILITY = Decimal("0.50")
ZERO = Decimal("0.00")
ONE = Decimal("1.00")
CV_NORMALISATION_DIVISOR = Decimal("0.3")

MIN_SAMPLES_FOR_VOLATILITY = 5
MIN_SAMPLES_FOR_ANOMALY = 10
ANOMALY_Z_THRESHOLD = Decimal("-2")
ANOMALY_WINDOW_DAYS = 14
VOLATILITY_WINDOW_DAYS = 30


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    is_anomaly: bool
    reason: str = "ok"
    z_score: Decimal | None = None
    srednia_okolic: Decimal | None = None
    odchylenie: Decimal | None = None
    spadek_procent: Decimal | None = None


class VolatilityCalculator:
    """Coefficient-of-variation-based price volatility score in [0, 1].

    See docs/analityka/wskaznik-zmiennosci.md.
    """

    def __init__(self, repo: HistoriaCenRepository | None = None) -> None:
        self.repo = repo or HistoriaCenRepository()

    def calculate(self, *, produkt_id: int, now: datetime | None = None) -> Decimal:
        now = now or datetime.now(UTC)
        since = now - timedelta(days=VOLATILITY_WINDOW_DAYS)
        history = self.repo.get_lowest_history(produkt_id=produkt_id, since=since)

        if len(history) < MIN_SAMPLES_FOR_VOLATILITY:
            return DEFAULT_VOLATILITY

        prices = pd.Series([float(row["cena"]) for row in history])
        mean = prices.mean()
        if mean == 0:
            return ZERO

        std = prices.std(ddof=1)
        if pd.isna(std):
            return ZERO

        cv = Decimal(str(std / mean))
        score = min(cv / CV_NORMALISATION_DIVISOR, ONE)
        return score.quantize(Decimal("0.01"))


def interval_minutes_for_volatility(score: Decimal) -> int:
    """Smart-polling cadence per docs/analityka/wskaznik-zmiennosci.md §4."""
    if score < Decimal("0.2"):
        return 1440
    if score < Decimal("0.4"):
        return 360
    if score < Decimal("0.6"):
        return 120
    if score < Decimal("0.8"):
        return 60
    return 15


class AnomalyDetector:
    """Detect flash-sale anomalies via Z-score over a 14-day window."""

    def __init__(self, repo: HistoriaCenRepository | None = None) -> None:
        self.repo = repo or HistoriaCenRepository()

    def check(
        self,
        *,
        produkt_id: int,
        aktualna_cena: Decimal,
        now: datetime | None = None,
    ) -> AnomalyResult:
        now = now or datetime.now(UTC)
        since = now - timedelta(days=ANOMALY_WINDOW_DAYS)
        stats = self.repo.get_stats(produkt_id=produkt_id, since=since)

        if stats["count"] < MIN_SAMPLES_FOR_ANOMALY:
            return AnomalyResult(is_anomaly=False, reason="insufficient_data")

        avg = stats["avg"]
        stddev = stats["stddev"]
        if avg is None or stddev is None or stddev == 0:
            return AnomalyResult(is_anomaly=False, reason="no_price_variation")

        avg_d = Decimal(str(avg))
        std_d = Decimal(str(stddev))
        z = (aktualna_cena - avg_d) / std_d
        spadek = (aktualna_cena - avg_d) / avg_d * Decimal("100")

        return AnomalyResult(
            is_anomaly=z < ANOMALY_Z_THRESHOLD,
            reason="anomaly" if z < ANOMALY_Z_THRESHOLD else "ok",
            z_score=z.quantize(Decimal("0.01")),
            srednia_okolic=avg_d.quantize(Decimal("0.01")),
            odchylenie=std_d.quantize(Decimal("0.01")),
            spadek_procent=spadek.quantize(Decimal("0.01")),
        )
