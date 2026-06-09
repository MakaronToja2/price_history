from __future__ import annotations

from .base import ScraperBase, WynikScrapowania


class AmazonScraper(ScraperBase):
    """Playwright-based scraper for amazon.pl.

    Stubbed for now; the real implementation lands in a later phase along
    with the Playwright browser bundle and a recorded HTML fixture.
    """

    platforma_nazwa = "amazon"

    def pobierz(self, identyfikator: str, typ_id: str) -> WynikScrapowania:
        raise NotImplementedError(
            "AmazonScraper is not yet implemented; Playwright integration "
            "is scheduled for the next iteration."
        )
