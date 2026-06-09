from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from groups.models import GrupaProduktow
from products.models import Platforma, Produkt
from users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def user() -> User:
    return User.objects.create_user(email="del@example.com", password="Pass1234!")


@pytest.fixture
def client(user: User) -> APIClient:
    api = APIClient()
    refresh = RefreshToken.for_user(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api


@pytest.fixture
def produkt(user: User) -> Produkt:
    grupa = GrupaProduktow.objects.create(uzytkownik=user, nazwa="G")
    return Produkt.objects.create(
        grupa=grupa,
        platforma=Platforma.objects.get(nazwa="allegro"),
        zewnetrzny_id="P-1",
        url="https://allegro.pl/oferta/1",
    )


class TestDeleteProduct:
    def test_marks_inactive(self, client: APIClient, produkt: Produkt) -> None:
        response = client.delete(f"/api/groups/{produkt.grupa_id}/products/{produkt.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        produkt.refresh_from_db()
        assert produkt.aktywny is False
        # Row preserved for historic charts
        assert Produkt.objects.filter(id=produkt.id).exists()

    def test_other_users_product_returns_404(self, client: APIClient) -> None:
        other = User.objects.create_user(email="x@y.com", password="Pass1234!")
        grupa = GrupaProduktow.objects.create(uzytkownik=other, nazwa="F")
        foreign = Produkt.objects.create(
            grupa=grupa,
            platforma=Platforma.objects.get(nazwa="allegro"),
            zewnetrzny_id="X",
            url="https://allegro.pl/oferta/x",
        )
        response = client.delete(f"/api/groups/{grupa.id}/products/{foreign.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        foreign.refresh_from_db()
        assert foreign.aktywny is True
