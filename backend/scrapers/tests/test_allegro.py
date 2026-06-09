from __future__ import annotations

from decimal import Decimal

import pytest
import responses
from django.core.cache import cache
from django.test import override_settings

from scrapers.allegro import AllegroAuthClient, AllegroClient, AllegroError
from scrapers.base import OfertaZewnetrzna, ProduktInfo


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_settings():
    with override_settings(
        ALLEGRO_CLIENT_ID="client123",
        ALLEGRO_CLIENT_SECRET="secret456",
        ALLEGRO_API_BASE_URL="https://api.allegro.pl",
        ALLEGRO_AUTH_URL="https://allegro.pl/auth/oauth/token",
    ):
        yield


class TestAllegroAuthClient:
    @responses.activate
    def test_fetches_and_caches_token(self, auth_settings) -> None:
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "abc.def.ghi", "expires_in": 43200},
            status=200,
        )

        client = AllegroAuthClient()
        token = client.get_token()
        assert token == "abc.def.ghi"

        client.get_token()
        client.get_token()
        assert len(responses.calls) == 1

    @responses.activate
    def test_force_refresh_skips_cache(self, auth_settings) -> None:
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "first", "expires_in": 43200},
            status=200,
        )
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "second", "expires_in": 43200},
            status=200,
        )

        client = AllegroAuthClient()
        assert client.get_token() == "first"
        assert client.get_token(force_refresh=True) == "second"

    @responses.activate
    def test_raises_on_auth_error(self, auth_settings) -> None:
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"error": "invalid_client"},
            status=401,
        )

        with pytest.raises(AllegroError):
            AllegroAuthClient().get_token()

    def test_raises_when_credentials_missing(self) -> None:
        with (
            override_settings(ALLEGRO_CLIENT_ID="", ALLEGRO_CLIENT_SECRET=""),
            pytest.raises(AllegroError, match="credentials"),
        ):
            AllegroAuthClient().get_token()


class TestAllegroClient:
    @responses.activate
    def test_fetch_offers_returns_mapped_offers(self, auth_settings) -> None:
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "tok", "expires_in": 43200},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.allegro.pl/offers/listing",
            json={
                "items": {
                    "regular": [
                        {
                            "id": "1",
                            "seller": {
                                "id": "S1",
                                "login": "SuperSklep",
                                "rating": {"positive": 99.8},
                            },
                            "sellingMode": {"price": {"amount": "2499.00", "currency": "PLN"}},
                        },
                        {
                            "id": "2",
                            "seller": {
                                "id": "S2",
                                "login": "TaniSprzet",
                                "rating": {"positive": 97.5},
                            },
                            "sellingMode": {"price": {"amount": "2599.00", "currency": "PLN"}},
                        },
                    ]
                },
                "searchMeta": {"availableCount": 2},
            },
            status=200,
        )

        client = AllegroClient()
        offers = client.fetch_offers(product_id="P-12345")

        assert len(offers) == 2
        assert offers[0] == OfertaZewnetrzna(
            sprzedawca_zewnetrzny_id="S1",
            sprzedawca_nazwa="SuperSklep",
            cena=Decimal("2499.00"),
            waluta="PLN",
            sprzedawca_ocena=Decimal("99.8"),
        )
        assert offers[1].sprzedawca_nazwa == "TaniSprzet"

    @responses.activate
    def test_fetch_offers_paginates(self, auth_settings) -> None:
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "tok", "expires_in": 43200},
            status=200,
        )

        page1 = {
            "items": {
                "regular": [
                    {
                        "id": str(i),
                        "seller": {"id": f"S{i}", "login": f"sklep{i}"},
                        "sellingMode": {"price": {"amount": f"{100 + i}.00", "currency": "PLN"}},
                    }
                    for i in range(60)
                ]
            },
            "searchMeta": {"availableCount": 75},
        }
        page2 = {
            "items": {
                "regular": [
                    {
                        "id": str(i),
                        "seller": {"id": f"S{i}", "login": f"sklep{i}"},
                        "sellingMode": {"price": {"amount": f"{200 + i}.00", "currency": "PLN"}},
                    }
                    for i in range(60, 75)
                ]
            },
            "searchMeta": {"availableCount": 75},
        }
        responses.add(
            responses.GET,
            "https://api.allegro.pl/offers/listing",
            json=page1,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.allegro.pl/offers/listing",
            json=page2,
            status=200,
        )

        offers = AllegroClient().fetch_offers(product_id="P-1")
        assert len(offers) == 75

    @responses.activate
    def test_fetch_product_details_returns_metadata(self, auth_settings) -> None:
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "tok", "expires_in": 43200},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.allegro.pl/sale/products/P-12345",
            json={
                "name": "Karta RTX 4080 SUPER",
                "images": [{"url": "https://img.cdn/rtx.jpg"}],
                "category": {"name": "Karty graficzne"},
            },
            status=200,
        )

        info = AllegroClient().fetch_product_details("P-12345")
        assert info == ProduktInfo(
            nazwa="Karta RTX 4080 SUPER",
            url_obrazka="https://img.cdn/rtx.jpg",
            kategoria="Karty graficzne",
        )

    @responses.activate
    def test_404_returns_empty_offers(self, auth_settings) -> None:
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "tok", "expires_in": 43200},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.allegro.pl/offers/listing",
            json={"error": "not_found"},
            status=404,
        )

        offers = AllegroClient().fetch_offers(product_id="P-missing")
        assert offers == []

    @responses.activate
    def test_401_triggers_token_refresh_once(self, auth_settings) -> None:
        # Initial auth
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "stale", "expires_in": 43200},
            status=200,
        )
        # 401 -> refresh
        responses.add(
            responses.GET,
            "https://api.allegro.pl/offers/listing",
            json={"error": "unauthorized"},
            status=401,
        )
        # Second auth
        responses.add(
            responses.POST,
            "https://allegro.pl/auth/oauth/token",
            json={"access_token": "fresh", "expires_in": 43200},
            status=200,
        )
        # Retry succeeds
        responses.add(
            responses.GET,
            "https://api.allegro.pl/offers/listing",
            json={
                "items": {
                    "regular": [
                        {
                            "id": "1",
                            "seller": {"id": "S1", "login": "X"},
                            "sellingMode": {"price": {"amount": "100.00", "currency": "PLN"}},
                        }
                    ]
                },
                "searchMeta": {"availableCount": 1},
            },
            status=200,
        )

        offers = AllegroClient().fetch_offers(product_id="P-1")
        assert len(offers) == 1
        assert offers[0].sprzedawca_zewnetrzny_id == "S1"
