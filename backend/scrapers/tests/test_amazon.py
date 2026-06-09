from __future__ import annotations

import pytest

from scrapers.amazon import AmazonScraper
from scrapers.base import ScraperBase


def test_amazon_scraper_is_a_scraper_base() -> None:
    assert issubclass(AmazonScraper, ScraperBase)


def test_amazon_scraper_pobierz_not_implemented() -> None:
    scraper = AmazonScraper()
    with pytest.raises(NotImplementedError):
        scraper.pobierz("B08N5WRWNW", "asin")
