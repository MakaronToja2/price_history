from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from groups.models import GrupaProduktow
from users.models import User


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(email="alerts@example.com", password="Pass1234!")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(email="other-alerts@example.com", password="Pass1234!")


@pytest.fixture
def grupa(user: User) -> GrupaProduktow:
    return GrupaProduktow.objects.create(uzytkownik=user, nazwa="Karta")


@pytest.fixture
def foreign_grupa(other_user: User) -> GrupaProduktow:
    return GrupaProduktow.objects.create(uzytkownik=other_user, nazwa="Foreign")


@pytest.fixture
def client(user: User) -> APIClient:
    api = APIClient()
    refresh = RefreshToken.for_user(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api


@pytest.fixture
def anon_client() -> APIClient:
    return APIClient()
