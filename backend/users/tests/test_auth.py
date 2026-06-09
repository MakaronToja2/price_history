from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User

VALID_PASSWORD = "SecurePass123!"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def existing_user() -> User:
    return User.objects.create_user(email="user@example.com", password=VALID_PASSWORD)


@pytest.fixture
def auth_client(api_client: APIClient, existing_user: User) -> APIClient:
    refresh = RefreshToken.for_user(existing_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.mark.django_db
class TestRegister:
    url = "/api/auth/register/"

    def test_creates_user_and_returns_tokens(self, api_client: APIClient) -> None:
        payload = {
            "email": "new@example.com",
            "password": VALID_PASSWORD,
            "password_confirm": VALID_PASSWORD,
        }
        response = api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["email"] == "new@example.com"
        assert "id" in body
        assert body["access"]
        assert body["refresh"]
        assert User.objects.filter(email="new@example.com").exists()

    def test_password_is_hashed(self, api_client: APIClient) -> None:
        api_client.post(
            self.url,
            {
                "email": "hash@example.com",
                "password": VALID_PASSWORD,
                "password_confirm": VALID_PASSWORD,
            },
            format="json",
        )
        user = User.objects.get(email="hash@example.com")
        assert user.password != VALID_PASSWORD
        assert user.check_password(VALID_PASSWORD)

    def test_rejects_mismatched_passwords(self, api_client: APIClient) -> None:
        response = api_client.post(
            self.url,
            {
                "email": "x@example.com",
                "password": VALID_PASSWORD,
                "password_confirm": "DifferentPass456!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(email="x@example.com").exists()

    def test_rejects_short_password(self, api_client: APIClient) -> None:
        response = api_client.post(
            self.url,
            {
                "email": "short@example.com",
                "password": "Ab1!",
                "password_confirm": "Ab1!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_duplicate_email(
        self,
        api_client: APIClient,
        existing_user: User,
    ) -> None:
        response = api_client.post(
            self.url,
            {
                "email": existing_user.email,
                "password": VALID_PASSWORD,
                "password_confirm": VALID_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_invalid_email(self, api_client: APIClient) -> None:
        response = api_client.post(
            self.url,
            {
                "email": "not-an-email",
                "password": VALID_PASSWORD,
                "password_confirm": VALID_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    url = "/api/auth/login/"

    def test_returns_tokens_on_valid_credentials(
        self,
        api_client: APIClient,
        existing_user: User,
    ) -> None:
        response = api_client.post(
            self.url,
            {"email": existing_user.email, "password": VALID_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["access"]
        assert body["refresh"]

    def test_rejects_wrong_password(
        self,
        api_client: APIClient,
        existing_user: User,
    ) -> None:
        response = api_client.post(
            self.url,
            {"email": existing_user.email, "password": "WrongPass!9"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_unknown_email(self, api_client: APIClient) -> None:
        response = api_client.post(
            self.url,
            {"email": "nobody@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRefresh:
    url = "/api/auth/refresh/"

    def test_returns_new_access_token(
        self,
        api_client: APIClient,
        existing_user: User,
    ) -> None:
        refresh = RefreshToken.for_user(existing_user)
        response = api_client.post(self.url, {"refresh": str(refresh)}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["access"]

    def test_rejects_invalid_refresh(self, api_client: APIClient) -> None:
        response = api_client.post(self.url, {"refresh": "not.a.token"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMe:
    url = "/api/auth/me/"

    def test_requires_authentication(self, api_client: APIClient) -> None:
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_current_user(
        self,
        auth_client: APIClient,
        existing_user: User,
    ) -> None:
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["id"] == existing_user.id
        assert body["email"] == existing_user.email
        assert "utworzono" in body
        assert body["liczba_grup"] == 0
        assert body["liczba_aktywnych_alertow"] == 0


def test_auth_urls_resolve() -> None:
    assert reverse("auth-register") == "/api/auth/register/"
    assert reverse("auth-login") == "/api/auth/login/"
    assert reverse("auth-refresh") == "/api/auth/refresh/"
    assert reverse("auth-me") == "/api/auth/me/"
