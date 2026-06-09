from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

Platforma = Literal["allegro", "amazon"]
TypId = Literal["offer", "product", "asin"]


class UnsupportedPlatformError(ValueError):
    """Raised when a URL does not match any supported platform."""


@dataclass(frozen=True, slots=True)
class PlatformaWykryta:
    platforma: Platforma
    typ_id: TypId
    identyfikator: str


_ALLEGRO_HOSTS = {"allegro.pl", "www.allegro.pl"}
_AMAZON_HOSTS = {"amazon.pl", "www.amazon.pl", "amazon.com", "www.amazon.com"}

_ALLEGRO_OFFER_RE = re.compile(r"^/oferta/(?:.*-)?(\d+)/?$")
_ALLEGRO_PRODUCT_RE = re.compile(r"^/produkt/([\w-]+)/?$")
_AMAZON_ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$|\?)")


def detect_platforma(url: str) -> PlatformaWykryta:
    """Identify the platform and extract the canonical product identifier.

    Raises:
        UnsupportedPlatformError: if the URL is malformed or not from a
            supported platform.
    """
    if not url or not url.startswith(("http://", "https://")):
        raise UnsupportedPlatformError(f"Not a valid URL: {url!r}")

    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if host in _ALLEGRO_HOSTS:
        return _detect_allegro(parsed.path)
    if host in _AMAZON_HOSTS:
        return _detect_amazon(url)

    raise UnsupportedPlatformError(f"Unsupported host: {host!r}")


def _detect_allegro(path: str) -> PlatformaWykryta:
    if match := _ALLEGRO_OFFER_RE.match(path):
        return PlatformaWykryta("allegro", "offer", match.group(1))
    if match := _ALLEGRO_PRODUCT_RE.match(path):
        return PlatformaWykryta("allegro", "product", match.group(1))
    raise UnsupportedPlatformError(
        f"Allegro URL has no recognised /oferta/ or /produkt/ path: {path!r}"
    )


def _detect_amazon(url: str) -> PlatformaWykryta:
    if match := _AMAZON_ASIN_RE.search(url):
        return PlatformaWykryta("amazon", "asin", match.group(1))
    raise UnsupportedPlatformError(f"Amazon URL has no ASIN: {url!r}")
