from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from groups.models import GrupaProduktow
from users.models import User

pytestmark = pytest.mark.django_db


class TestList:
    url = "/api/groups/"

    def test_requires_auth(self, anon_client: APIClient) -> None:
        assert anon_client.get(self.url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_only_owned_groups(
        self,
        client: APIClient,
        user: User,
        other_user: User,
    ) -> None:
        GrupaProduktow.objects.create(uzytkownik=user, nazwa="Mine")
        GrupaProduktow.objects.create(uzytkownik=other_user, nazwa="Theirs")

        response = client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["count"] == 1
        assert body["results"][0]["nazwa"] == "Mine"

    def test_supports_search(self, client: APIClient, user: User) -> None:
        GrupaProduktow.objects.create(uzytkownik=user, nazwa="RTX 4080")
        GrupaProduktow.objects.create(uzytkownik=user, nazwa="Ryzen 9")

        response = client.get(self.url + "?search=rtx")
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["nazwa"] == "RTX 4080"

    def test_filter_by_aktywny(self, client: APIClient, user: User) -> None:
        GrupaProduktow.objects.create(uzytkownik=user, nazwa="A", aktywny=True)
        GrupaProduktow.objects.create(uzytkownik=user, nazwa="B", aktywny=False)

        response = client.get(self.url + "?aktywny=true")
        results = response.json()["results"]
        assert {g["nazwa"] for g in results} == {"A"}


class TestCreate:
    url = "/api/groups/"

    def test_creates_group_owned_by_caller(self, client: APIClient, user: User) -> None:
        response = client.post(
            self.url,
            {"nazwa": "RTX 4080", "opis": "GPU", "cena_docelowa": "2200.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["nazwa"] == "RTX 4080"
        assert body["aktywny"] is True
        assert GrupaProduktow.objects.filter(uzytkownik=user, nazwa="RTX 4080").exists()

    def test_rejects_missing_nazwa(self, client: APIClient) -> None:
        response = client.post(self.url, {"opis": "no name"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ignores_uzytkownik_in_payload(
        self, client: APIClient, user: User, other_user: User
    ) -> None:
        response = client.post(
            self.url,
            {"nazwa": "Hijack", "uzytkownik": other_user.id},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        group = GrupaProduktow.objects.get(nazwa="Hijack")
        assert group.uzytkownik == user


class TestRetrieve:
    def url(self, pk: int) -> str:
        return f"/api/groups/{pk}/"

    def test_returns_own_group(self, client: APIClient, group: GrupaProduktow) -> None:
        response = client.get(self.url(group.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == group.id

    def test_includes_produkty_list(self, client: APIClient, group: GrupaProduktow) -> None:
        response = client.get(self.url(group.id))
        body = response.json()
        assert "produkty" in body
        assert body["produkty"] == []

    def test_404_for_other_users_group(self, client: APIClient, other_user: User) -> None:
        foreign = GrupaProduktow.objects.create(uzytkownik=other_user, nazwa="Foreign")
        response = client.get(self.url(foreign.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdate:
    def url(self, pk: int) -> str:
        return f"/api/groups/{pk}/"

    def test_patch_updates_fields(self, client: APIClient, group: GrupaProduktow) -> None:
        response = client.patch(
            self.url(group.id),
            {"cena_docelowa": "2100.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        group.refresh_from_db()
        assert str(group.cena_docelowa) == "2100.00"

    def test_cannot_change_owner(
        self,
        client: APIClient,
        group: GrupaProduktow,
        other_user: User,
    ) -> None:
        client.patch(
            self.url(group.id),
            {"uzytkownik": other_user.id},
            format="json",
        )
        group.refresh_from_db()
        assert group.uzytkownik_id != other_user.id

    def test_cannot_update_other_users_group(self, client: APIClient, other_user: User) -> None:
        foreign = GrupaProduktow.objects.create(uzytkownik=other_user, nazwa="X")
        response = client.patch(self.url(foreign.id), {"nazwa": "hacked"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDelete:
    def url(self, pk: int) -> str:
        return f"/api/groups/{pk}/"

    def test_deletes_own_group(self, client: APIClient, group: GrupaProduktow) -> None:
        response = client.delete(self.url(group.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not GrupaProduktow.objects.filter(id=group.id).exists()

    def test_cannot_delete_other_users_group(self, client: APIClient, other_user: User) -> None:
        foreign = GrupaProduktow.objects.create(uzytkownik=other_user, nazwa="X")
        response = client.delete(self.url(foreign.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert GrupaProduktow.objects.filter(id=foreign.id).exists()


def test_group_urls_resolve() -> None:
    assert reverse("group-list") == "/api/groups/"
    assert reverse("group-detail", kwargs={"pk": 1}) == "/api/groups/1/"


@pytest.mark.django_db
class TestMeUserCount:
    def test_liczba_grup_reflects_real_count(self, client: APIClient, user: User) -> None:
        GrupaProduktow.objects.create(uzytkownik=user, nazwa="A")
        GrupaProduktow.objects.create(uzytkownik=user, nazwa="B")

        response = client.get("/api/auth/me/")
        assert response.json()["liczba_grup"] == 2
