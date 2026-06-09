from __future__ import annotations

from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

from .base import OfertaZewnetrzna, ProduktInfo, ScraperBase, WynikScrapowania


class AllegroError(RuntimeError):
    """Raised for any non-recoverable Allegro API failure."""


class AllegroAuthClient:
    """Manages OAuth2 client_credentials tokens, cached in Django's cache."""

    CACHE_KEY = "allegro:access_token"
    TTL_BUFFER_SECONDS = 300
    REQUEST_TIMEOUT_SECONDS = 10

    def get_token(self, *, force_refresh: bool = False) -> str:
        if not force_refresh:
            cached = cache.get(self.CACHE_KEY)
            if cached:
                return str(cached)

        return self._fetch_new_token()

    def _fetch_new_token(self) -> str:
        client_id = settings.ALLEGRO_CLIENT_ID
        client_secret = settings.ALLEGRO_CLIENT_SECRET
        if not client_id or not client_secret:
            raise AllegroError(
                "Missing Allegro credentials: set ALLEGRO_CLIENT_ID and "
                "ALLEGRO_CLIENT_SECRET in the environment."
            )

        try:
            response = requests.post(
                settings.ALLEGRO_AUTH_URL,
                auth=(client_id, client_secret),
                data={"grant_type": "client_credentials"},
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise AllegroError(f"OAuth network failure: {exc}") from exc

        if response.status_code != 200:
            raise AllegroError(f"OAuth failed: HTTP {response.status_code} — {response.text[:200]}")

        data = response.json()
        token = data["access_token"]
        ttl = max(60, int(data["expires_in"]) - self.TTL_BUFFER_SECONDS)
        cache.set(self.CACHE_KEY, token, ttl)
        return str(token)


class AllegroClient(ScraperBase):
    """High-level client for fetching offers and product metadata from Allegro."""

    platforma_nazwa = "allegro"

    PAGE_SIZE = 60
    HARD_OFFSET_LIMIT = 300
    REQUEST_TIMEOUT_SECONDS = 10
    ACCEPT_HEADER = "application/vnd.allegro.public.v1+json"

    def __init__(self, auth_client: AllegroAuthClient | None = None) -> None:
        self.auth = auth_client or AllegroAuthClient()

    # ScraperBase API -----------------------------------------------------

    def pobierz(self, identyfikator: str, typ_id: str) -> WynikScrapowania:
        if typ_id != "product":
            raise AllegroError(
                f"AllegroClient.pobierz requires product_id; got typ_id={typ_id!r}. "
                "Resolve offer->product via Allegro before fetching."
            )
        info = self.fetch_product_details(identyfikator)
        oferty = self.fetch_offers(product_id=identyfikator)
        return WynikScrapowania(produkt=info, oferty=oferty)

    # Concrete operations -------------------------------------------------

    def fetch_offers(self, *, product_id: str) -> list[OfertaZewnetrzna]:
        offers: list[OfertaZewnetrzna] = []
        offset = 0
        while offset < self.HARD_OFFSET_LIMIT:
            data = self._get(
                "/offers/listing",
                params={
                    "product.id": product_id,
                    "sort": "+price",
                    "limit": self.PAGE_SIZE,
                    "offset": offset,
                },
                allow_404=True,
            )
            if data is None:
                return []

            page = data.get("items", {}).get("regular", [])
            if not page:
                break

            offers.extend(_map_offer(o) for o in page)

            total = int(data.get("searchMeta", {}).get("availableCount", 0))
            offset += self.PAGE_SIZE
            if offset >= total:
                break

        return offers

    def fetch_product_details(self, product_id: str) -> ProduktInfo:
        data = self._get(f"/sale/products/{product_id}")
        assert data is not None  # 404 not requested
        images = data.get("images") or []
        return ProduktInfo(
            nazwa=data.get("name", ""),
            url_obrazka=images[0]["url"] if images else None,
            kategoria=(data.get("category") or {}).get("name"),
        )

    # HTTP helpers --------------------------------------------------------

    def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        allow_404: bool = False,
        _retried: bool = False,
    ) -> dict[str, Any] | None:
        url = f"{settings.ALLEGRO_API_BASE_URL}{path}"
        token = self.auth.get_token()
        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": self.ACCEPT_HEADER,
                },
                params=params,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise AllegroError(f"Network error fetching {url}: {exc}") from exc

        if response.status_code == 401 and not _retried:
            self.auth.get_token(force_refresh=True)
            return self._get(path, params=params, allow_404=allow_404, _retried=True)

        if response.status_code == 404 and allow_404:
            return None

        if response.status_code != 200:
            raise AllegroError(f"HTTP {response.status_code} from {url}: {response.text[:200]}")

        return response.json()


def _map_offer(offer: dict[str, Any]) -> OfertaZewnetrzna:
    seller = offer.get("seller") or {}
    price = (offer.get("sellingMode") or {}).get("price") or {}
    rating = (seller.get("rating") or {}).get("positive")
    return OfertaZewnetrzna(
        sprzedawca_zewnetrzny_id=str(seller.get("id", "")),
        sprzedawca_nazwa=str(seller.get("login", "")),
        cena=Decimal(str(price.get("amount", "0"))),
        waluta=str(price.get("currency", "PLN")),
        sprzedawca_ocena=Decimal(str(rating)) if rating is not None else None,
    )
