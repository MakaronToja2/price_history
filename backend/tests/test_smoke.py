"""Phase 0 smoke tests — verify project skeleton is wired correctly."""

from django.conf import settings


def test_settings_loaded() -> None:
    assert settings.SECRET_KEY
    assert "default" in settings.DATABASES
    assert "timeseries" in settings.DATABASES


def test_local_apps_registered() -> None:
    expected = {
        "users",
        "groups",
        "products",
        "sellers",
        "alerts",
        "analytics",
        "scrapers",
    }
    assert expected.issubset(set(settings.INSTALLED_APPS))


def test_database_router_configured() -> None:
    assert "config.routers.PriceHistoryRouter" in settings.DATABASE_ROUTERS


def test_celery_app_importable() -> None:
    from config import celery_app

    assert celery_app.main == "price_history"
    queue_names = {q.name for q in celery_app.conf.task_queues}
    assert queue_names == {"wysoki_priorytet", "niski_priorytet", "powiadomienia"}


def test_custom_user_model_uses_polish_table() -> None:
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    assert user_model._meta.db_table == "uzytkownicy"
    assert user_model.USERNAME_FIELD == "email"


def test_jwt_lifetimes_configured() -> None:
    assert "ACCESS_TOKEN_LIFETIME" in settings.SIMPLE_JWT
    assert "REFRESH_TOKEN_LIFETIME" in settings.SIMPLE_JWT


def test_locale_is_polish() -> None:
    assert settings.LANGUAGE_CODE == "pl"
    assert settings.TIME_ZONE == "Europe/Warsaw"
