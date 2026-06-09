from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from alerts.models import Alert
from groups.models import GrupaProduktow

pytestmark = pytest.mark.django_db


class TestList:
    url = "/api/alerts/"

    def test_requires_auth(self, anon_client: APIClient) -> None:
        assert anon_client.get(self.url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_only_user_alerts(
        self,
        client: APIClient,
        grupa: GrupaProduktow,
        foreign_grupa: GrupaProduktow,
    ) -> None:
        Alert.objects.create(
            grupa=grupa, typ_alertu=Alert.TYP_DOCELOWY, prog_ceny=Decimal("100.00")
        )
        Alert.objects.create(
            grupa=foreign_grupa,
            typ_alertu=Alert.TYP_DOCELOWY,
            prog_ceny=Decimal("999.00"),
        )

        response = client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["count"] == 1
        assert body["results"][0]["grupa_nazwa"] == grupa.nazwa


class TestCreate:
    def _url(self, grupa_id: int) -> str:
        return f"/api/groups/{grupa_id}/alerts/"

    def test_creates_docelowy(self, client: APIClient, grupa: GrupaProduktow) -> None:
        response = client.post(
            self._url(grupa.id),
            {"typ_alertu": "docelowy", "prog_ceny": "2200.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Alert.objects.filter(grupa=grupa, typ_alertu="docelowy").exists()

    def test_creates_spadek_ceny(self, client: APIClient, grupa: GrupaProduktow) -> None:
        response = client.post(
            self._url(grupa.id),
            {"typ_alertu": "spadek_ceny", "prog_procent": "10.0"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_creates_flash_sale_without_thresholds(
        self, client: APIClient, grupa: GrupaProduktow
    ) -> None:
        response = client.post(
            self._url(grupa.id),
            {"typ_alertu": "flash_sale"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_docelowy_requires_prog_ceny(self, client: APIClient, grupa: GrupaProduktow) -> None:
        response = client.post(
            self._url(grupa.id),
            {"typ_alertu": "docelowy"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_create_alert_in_other_users_group(
        self, client: APIClient, foreign_grupa: GrupaProduktow
    ) -> None:
        response = client.post(
            self._url(foreign_grupa.id),
            {"typ_alertu": "docelowy", "prog_ceny": "100.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateDelete:
    def test_patch_updates_threshold(self, client: APIClient, grupa: GrupaProduktow) -> None:
        alert = Alert.objects.create(
            grupa=grupa, typ_alertu=Alert.TYP_DOCELOWY, prog_ceny=Decimal("100")
        )
        response = client.patch(
            f"/api/alerts/{alert.id}/",
            {"prog_ceny": "150.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        alert.refresh_from_db()
        assert alert.prog_ceny == Decimal("150.00")

    def test_delete_removes_alert(self, client: APIClient, grupa: GrupaProduktow) -> None:
        alert = Alert.objects.create(
            grupa=grupa, typ_alertu=Alert.TYP_DOCELOWY, prog_ceny=Decimal("100")
        )
        response = client.delete(f"/api/alerts/{alert.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Alert.objects.filter(id=alert.id).exists()

    def test_cannot_modify_other_users_alert(
        self, client: APIClient, foreign_grupa: GrupaProduktow
    ) -> None:
        alert = Alert.objects.create(
            grupa=foreign_grupa,
            typ_alertu=Alert.TYP_DOCELOWY,
            prog_ceny=Decimal("100"),
        )
        response = client.patch(
            f"/api/alerts/{alert.id}/",
            {"prog_ceny": "0"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
