from __future__ import annotations

import html
import logging
import re
from decimal import Decimal, InvalidOperation

from .base import OfertaZewnetrzna, ProduktInfo, ScraperBase, WynikScrapowania

logger = logging.getLogger(__name__)


class AmazonScraperError(RuntimeError):
    """Raised when scraping fails irrecoverably (CAPTCHA, layout change, etc)."""


# Amazon's buy box is rendered into one of several containers depending on the
# A/B test bucket. We try the broadest selectors and fall back to a regex.
_TITLE_SELECTORS = ("#productTitle",)
_PRICE_SELECTORS = (
    "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
    "#corePrice_feature_div .a-price .a-offscreen",
    ".a-price .a-offscreen",
)
_SELLER_SELECTORS = (
    "#sellerProfileTriggerId",
    "#merchant-info a",
    "#tabular-buybox .tabular-buybox-text",
)

_PRICE_NUMBER_RE = re.compile(r"(\d[\d\s ]*[.,]?\d*)")


class AmazonScraper(ScraperBase):
    """Playwright-based scraper for amazon.pl product pages.

    Only the visible buy-box is parsed (single offer per page). The
    "Other sellers" flyout is gated by anti-bot checks and intentionally
    skipped. Use Allegro when cross-seller data matters.
    """

    platforma_nazwa = "amazon"

    BASE_URL = "https://www.amazon.pl"
    DEFAULT_TIMEOUT_MS = 20_000

    def __init__(
        self,
        *,
        timeout_ms: int | None = None,
        locale: str = "pl-PL",
    ) -> None:
        self.timeout_ms = timeout_ms or self.DEFAULT_TIMEOUT_MS
        self.locale = locale

    def pobierz(self, identyfikator: str, typ_id: str) -> WynikScrapowania:
        if typ_id != "asin":
            raise AmazonScraperError(f"AmazonScraper requires typ_id='asin'; got {typ_id!r}")
        url = f"{self.BASE_URL}/dp/{identyfikator}"
        html = self._fetch_html(url)
        return _parse_amazon_page(html)

    def _fetch_html(self, url: str) -> str:
        from playwright.sync_api import TimeoutError as PWTimeout
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    locale=self.locale,
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()
                try:
                    page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
                    page.wait_for_selector("#productTitle", timeout=self.timeout_ms)
                except PWTimeout as exc:
                    raise AmazonScraperError(
                        f"Timeout loading {url}; Amazon may have shown a CAPTCHA."
                    ) from exc
                return page.content()
            finally:
                browser.close()


def _parse_amazon_page(html: str) -> WynikScrapowania:
    """Pure HTML parser; isolated from Playwright so tests can drive it
    with a stored fixture and unit-test the extraction logic."""
    extracted = _AmazonExtractor()
    extracted.feed(html)

    nazwa = (extracted.title or "").strip()
    cena_str = (extracted.price or "").strip()
    sprzedawca = (extracted.seller or "Amazon").strip()
    img = extracted.image

    if not nazwa or not cena_str:
        raise AmazonScraperError(
            "Could not extract title/price from page (selector layout changed?)."
        )

    cena = _parse_price(cena_str)
    if cena is None:
        raise AmazonScraperError(f"Could not parse price string {cena_str!r}.")

    oferta = OfertaZewnetrzna(
        sprzedawca_zewnetrzny_id=sprzedawca,
        sprzedawca_nazwa=sprzedawca,
        cena=cena,
        waluta="PLN",
    )
    return WynikScrapowania(produkt=ProduktInfo(nazwa=nazwa, url_obrazka=img), oferty=[oferta])


def _parse_price(raw: str) -> Decimal | None:
    """Amazon prices arrive as '999,00 zł' / '1 999,99 zł' etc.
    Strip non-numeric noise, convert comma to dot, return Decimal."""
    match = _PRICE_NUMBER_RE.search(raw)
    if not match:
        return None
    cleaned = match.group(1)
    cleaned = cleaned.replace(" ", "").replace(" ", "")
    cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


class _AmazonExtractor:
    """Minimal HTML walker that pulls just the fields we need."""

    def __init__(self) -> None:
        self.title: str | None = None
        self.price: str | None = None
        self.seller: str | None = None
        self.image: str | None = None
        self._buf: list[str] = []
        self._capture: str | None = None

    def feed(self, raw_html: str) -> None:
        # Title: id="productTitle"
        if m := re.search(r'<[^>]+id="productTitle"[^>]*>([^<]+)</', raw_html, re.IGNORECASE):
            self.title = html.unescape(m.group(1))

        # Price: prefer .a-offscreen inside #corePriceDisplay_desktop_feature_div.
        # Real-world Amazon often renders an empty .a-offscreen in the desktop
        # container while the real number lives in #corePrice_feature_div — skip
        # whitespace-only matches and continue to the next pattern. HTML entities
        # like `&nbsp;` (between thousands and hundreds: "8&nbsp;195,00zł") must
        # be decoded before regex parsing, else only the leading digit is captured.
        for pattern in (
            r'id="corePriceDisplay_desktop_feature_div".*?class="a-offscreen"[^>]*>([^<]+)<',
            r'id="corePrice_feature_div".*?class="a-offscreen"[^>]*>([^<]+)<',
            r'class="a-offscreen"[^>]*>([^<]+)<',
        ):
            for m in re.finditer(pattern, raw_html, re.IGNORECASE | re.DOTALL):
                candidate = html.unescape(m.group(1)).strip()
                if candidate:
                    self.price = candidate
                    break
            if self.price:
                break

        # Seller name
        for pattern in (
            r'id="sellerProfileTriggerId"[^>]*>([^<]+)<',
            r'id="merchant-info"[^>]*>.*?<a[^>]*>([^<]+)<',
        ):
            if m := re.search(pattern, raw_html, re.IGNORECASE | re.DOTALL):
                self.seller = html.unescape(m.group(1))
                break

        # Main image
        if m := re.search(r'id="landingImage"[^>]*src="([^"]+)"', raw_html, re.IGNORECASE):
            self.image = m.group(1)
