from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OfertaZewnetrzna:
    """A single seller's offer for a product on a given platform."""

    sprzedawca_zewnetrzny_id: str
    sprzedawca_nazwa: str
    cena: Decimal
    waluta: str = "PLN"
    sprzedawca_ocena: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ProduktInfo:
    """Metadata for a product (fetched on first add or refresh)."""

    nazwa: str
    url_obrazka: str | None = None
    kategoria: str | None = None


@dataclass(frozen=True, slots=True)
class WynikScrapowania:
    """Combined output of fetching prices for a single product."""

    produkt: ProduktInfo
    oferty: list[OfertaZewnetrzna] = field(default_factory=list)


class ScraperBase(ABC):
    """Common interface every platform scraper must satisfy.

    `identyfikator` is the canonical platform ID returned by
    `scrapers.detection.detect_platforma` (offer/product/asin).
    """

    platforma_nazwa: str

    @abstractmethod
    def pobierz(self, identyfikator: str, typ_id: str) -> WynikScrapowania:
        """Fetch offers and metadata for a product."""
