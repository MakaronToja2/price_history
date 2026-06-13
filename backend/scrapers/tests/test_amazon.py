from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from scrapers.amazon import (
    AmazonScraper,
    AmazonScraperError,
    _parse_amazon_page,
    _parse_price,
)
from scrapers.base import ScraperBase


def test_amazon_scraper_is_a_scraper_base() -> None:
    assert issubclass(AmazonScraper, ScraperBase)


def test_amazon_requires_asin_typ_id() -> None:
    with pytest.raises(AmazonScraperError, match="asin"):
        AmazonScraper().pobierz("B08N5WRWNW", "offer")


_SAMPLE_HTML = """
<html><body>
  <h1>
    <span id="productTitle">Karta graficzna NVIDIA RTX 4080 SUPER 16GB</span>
  </h1>
  <img id="landingImage" src="https://images-na.ssl/rtx.jpg" />
  <div id="corePriceDisplay_desktop_feature_div">
    <span class="a-price">
      <span class="a-offscreen">2 399,00 zł</span>
    </span>
  </div>
  <div id="merchant-info">
    Sprzedawca: <a href="/seller/x">TechMagazyn PL</a>
  </div>
</body></html>
"""


class TestParser:
    def test_extracts_title_price_seller_image(self) -> None:
        wynik = _parse_amazon_page(_SAMPLE_HTML)
        assert wynik.produkt.nazwa == "Karta graficzna NVIDIA RTX 4080 SUPER 16GB"
        assert wynik.produkt.url_obrazka == "https://images-na.ssl/rtx.jpg"
        assert len(wynik.oferty) == 1
        oferta = wynik.oferty[0]
        assert oferta.cena == Decimal("2399.00")
        assert oferta.sprzedawca_nazwa == "TechMagazyn PL"
        assert oferta.waluta == "PLN"

    def test_falls_back_to_generic_offscreen_price(self) -> None:
        html = """
        <html><body>
          <span id="productTitle">Drobiazg</span>
          <span class="a-offscreen">19,99 zł</span>
        </body></html>
        """
        wynik = _parse_amazon_page(html)
        assert wynik.oferty[0].cena == Decimal("19.99")
        # No merchant block → fall back to 'Amazon'
        assert wynik.oferty[0].sprzedawca_nazwa == "Amazon"

    def test_raises_when_title_missing(self) -> None:
        html = '<html><body><span class="a-offscreen">10 zł</span></body></html>'
        with pytest.raises(AmazonScraperError):
            _parse_amazon_page(html)

    def test_raises_when_price_missing(self) -> None:
        html = '<html><body><span id="productTitle">Produkt</span></body></html>'
        with pytest.raises(AmazonScraperError):
            _parse_amazon_page(html)

    def test_decodes_html_nbsp_entity_in_price(self) -> None:
        # Real-world amazon.pl serves "8&nbsp;195,00zł" as HTML entities, not
        # raw NBSP. Without entity decoding the price regex captures only "8".
        # Observed live on B0GKZMFC2K (Sauna Ogrodowa QUADRO).
        html = """
        <html><body>
          <span id="productTitle">Sauna QUADRO</span>
          <div id="corePrice_feature_div">
            <span class="a-price"><span class="a-offscreen">8&nbsp;195,00&nbsp;zł</span></span>
          </div>
        </body></html>
        """
        wynik = _parse_amazon_page(html)
        assert wynik.oferty[0].cena == Decimal("8195.00")

    def test_skips_empty_offscreen_when_real_price_exists_in_next_container(self) -> None:
        # Real-world amazon.pl quirk (observed on B07GWBL5VW "Kind of Blue"):
        # #corePriceDisplay_desktop_feature_div contains a whitespace-only
        # .a-offscreen, while #corePrice_feature_div has the actual price.
        # The parser must skip empty matches and fall through to the next pattern.
        html = """
        <html><body>
          <span id="productTitle">Kind Of Blue</span>
          <div id="corePriceDisplay_desktop_feature_div">
            <span class="a-price"><span class="a-offscreen"> </span></span>
          </div>
          <div id="corePrice_feature_div">
            <span class="a-price"><span class="a-offscreen">66,97 zł</span></span>
          </div>
        </body></html>
        """
        wynik = _parse_amazon_page(html)
        assert wynik.oferty[0].cena == Decimal("66.97")


class TestPriceParse:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2 399,00 zł", Decimal("2399.00")),
            ("19,99 zł", Decimal("19.99")),
            ("1 234 567,89 PLN", Decimal("1234567.89")),
            ("100", Decimal("100")),
            ("100.50", Decimal("100.50")),
        ],
    )
    def test_parses_polish_format(self, raw: str, expected: Decimal) -> None:
        assert _parse_price(raw) == expected

    def test_returns_none_for_garbage(self) -> None:
        assert _parse_price("brak danych") is None


class TestScraperPlaywrightWiring:
    def test_uses_playwright_and_returns_parsed_result(self) -> None:
        """End-to-end inside the scraper: mock sync_playwright, verify
        the scraper builds the URL, calls goto, returns parsed page."""
        page = MagicMock()
        page.content.return_value = _SAMPLE_HTML
        context = MagicMock()
        context.new_page.return_value = page
        browser = MagicMock()
        browser.new_context.return_value = context
        pw_instance = MagicMock()
        pw_instance.chromium.launch.return_value = browser

        pw_ctx = MagicMock()
        pw_ctx.__enter__.return_value = pw_instance
        pw_ctx.__exit__.return_value = False

        with patch("playwright.sync_api.sync_playwright", return_value=pw_ctx):
            wynik = AmazonScraper().pobierz("B08N5WRWNW", "asin")

        page.goto.assert_called_once()
        url = page.goto.call_args.args[0]
        assert url == "https://www.amazon.pl/dp/B08N5WRWNW"
        assert wynik.produkt.nazwa.startswith("Karta graficzna")
        assert wynik.oferty[0].cena == Decimal("2399.00")
        browser.close.assert_called_once()
