from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from groups.models import GrupaProduktow
from users.models import User


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(email="owner@example.com", password="Pass1234!")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(email="other@example.com", password="Pass1234!")


@pytest.fixture
def client(user: User) -> APIClient:
    api = APIClient()
    refresh = RefreshToken.for_user(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api


@pytest.fixture
def anon_client() -> APIClient:
    return APIClient()


@pytest.fixture
def group(user: User) -> GrupaProduktow:
    return GrupaProduktow.objects.create(
        uzytkownik=user,
        nazwa="RTX 4080",
        opis="Karta graficzna",
        cena_docelowa="2200.00",
    )
