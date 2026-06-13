from __future__ import annotations

import pytest

from scrapers.detection import (
    PlatformaWykryta,
    UnsupportedPlatformError,
    detect_platforma,
)


class TestAllegroDetection:
    @pytest.mark.parametrize(
        ("url", "expected_id"),
        [
            ("https://allegro.pl/oferta/karta-rtx-4080-12345678", "12345678"),
            ("https://allegro.pl/oferta/12345678", "12345678"),
            ("https://allegro.pl/oferta/12345678/", "12345678"),
            ("https://allegro.pl/oferta/karta-rtx-4080-12345678?bla=1", "12345678"),
            ("http://allegro.pl/oferta/karta-rtx-4080-12345678", "12345678"),
        ],
    )
    def test_extracts_offer_id(self, url: str, expected_id: str) -> None:
        result = detect_platforma(url)
        assert result.platforma == "allegro"
        assert result.identyfikator == expected_id
        assert result.typ_id == "offer"

    @pytest.mark.parametrize(
        ("url", "expected_uuid"),
        [
            # Allegro /produkt/ URLs end with a UUID — only the UUID is a valid
            # product identifier for /sale/products/{id}. The slug prefix is
            # human-readable filler, useless to the API.
            (
                "https://allegro.pl/produkt/karta-graficzna-rtx-4080-2b3c8184-d0a2-48c8-998b-72c4e6495b0f",
                "2b3c8184-d0a2-48c8-998b-72c4e6495b0f",
            ),
            (
                "https://allegro.pl/produkt/sauna-beczka-200-x-150-1fdb9b19-552e-41ad-a35f-f32a12b2f55e/",
                "1fdb9b19-552e-41ad-a35f-f32a12b2f55e",
            ),
            (
                "https://allegro.pl/produkt/karta-graficzna-rtx-4080-2b3c8184-d0a2-48c8-998b-72c4e6495b0f?bla=1",
                "2b3c8184-d0a2-48c8-998b-72c4e6495b0f",
            ),
        ],
    )
    def test_extracts_product_uuid(self, url: str, expected_uuid: str) -> None:
        result = detect_platforma(url)
        assert result.platforma == "allegro"
        assert result.identyfikator == expected_uuid
        assert result.typ_id == "product"

    def test_rejects_product_url_without_uuid(self) -> None:
        with pytest.raises(UnsupportedPlatformError):
            detect_platforma("https://allegro.pl/produkt/karta-graficzna-rtx-4080-super")


class TestAmazonDetection:
    @pytest.mark.parametrize(
        ("url", "expected_asin"),
        [
            ("https://www.amazon.pl/dp/B08N5WRWNW", "B08N5WRWNW"),
            ("https://amazon.pl/dp/B08N5WRWNW", "B08N5WRWNW"),
            ("https://www.amazon.pl/dp/B08N5WRWNW/ref=foo", "B08N5WRWNW"),
            ("https://amazon.com/dp/B08N5WRWNW", "B08N5WRWNW"),
            (
                "https://www.amazon.pl/Karta-graficzna/dp/B08N5WRWNW/ref=bar",
                "B08N5WRWNW",
            ),
            (
                "https://amazon.pl/gp/product/B08N5WRWNW/foo",
                "B08N5WRWNW",
            ),
        ],
    )
    def test_extracts_asin(self, url: str, expected_asin: str) -> None:
        result = detect_platforma(url)
        assert result.platforma == "amazon"
        assert result.identyfikator == expected_asin
        assert result.typ_id == "asin"


class TestUnsupported:
    @pytest.mark.parametrize(
        "url",
        [
            "https://ebay.com/itm/12345",
            "https://google.com",
            "not-a-url",
            "",
            "https://allegro.pl/help/some-page",
        ],
    )
    def test_raises(self, url: str) -> None:
        with pytest.raises(UnsupportedPlatformError):
            detect_platforma(url)


def test_returns_named_tuple_shape() -> None:
    result = detect_platforma("https://allegro.pl/oferta/12345678")
    assert isinstance(result, PlatformaWykryta)
