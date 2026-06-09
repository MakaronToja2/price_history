"""
Django settings for Price History Scanner.

Environment-driven configuration; see `.env.example` at repo root.
"""

from datetime import timedelta
from pathlib import Path

from decouple import AutoConfig, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# Look for .env at repo root (one level above the backend/ directory).
config = AutoConfig(search_path=BASE_DIR.parent)

SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-development-key-change-me-in-production",
)
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="*", cast=Csv())


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    # Local
    "users",
    "groups",
    "products",
    "sellers",
    "alerts",
    "analytics",
    "scrapers",
]

if DEBUG:
    INSTALLED_APPS += ["django_extensions"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# Databases
# ---------------------------------------------------------------------------
# Dual-database setup: PostgreSQL for transactional data, TimescaleDB for
# time-series. See docs/baza-danych/schemat-postgresql.md and schemat-timescaledb.md.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="price_history"),
        "USER": config("POSTGRES_USER", default="postgres"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="postgres"),
        "HOST": config("POSTGRES_HOST", default="db"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    },
    "timeseries": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("TIMESCALE_DB", default="price_timeseries"),
        "USER": config("TIMESCALE_USER", default="postgres"),
        "PASSWORD": config("TIMESCALE_PASSWORD", default="postgres"),
        "HOST": config("TIMESCALE_HOST", default="timescaledb"),
        "PORT": config("TIMESCALE_PORT", default="5432"),
        "TEST": {"DEPENDENCIES": []},
    },
}

DATABASE_ROUTERS = ["config.routers.PriceHistoryRouter"]

AUTH_USER_MODEL = "users.User"


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    # Notes: DRF only supports s/m/h/d suffixes, so the 5/15min target from
    # docs/api/endpointy.md §8 is approximated as 5/m (a tighter window).
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/hour",
        "anon": "100/hour",
        "login": "5/min",
        "register": "3/hour",
        "refresh-group": "1/min",
    },
}


# ---------------------------------------------------------------------------
# JWT (SimpleJWT)
# ---------------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_LIFETIME_MINUTES", default=15, cast=int),
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_LIFETIME_DAYS", default=7, cast=int),
    ),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
}


# ---------------------------------------------------------------------------
# OpenAPI / Swagger (drf-spectacular)
# ---------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "Price History Scanner API",
    "DESCRIPTION": "REST API for multi-platform price tracking (PZSI 2025)",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth", "description": "Rejestracja, logowanie, JWT"},
        {"name": "groups", "description": "Grupy produktów (cross-platform)"},
        {"name": "products", "description": "Produkty w ramach grupy"},
        {"name": "alerts", "description": "Alerty cenowe"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
    "SECURITY": [{"BearerAuth": []}],
}


# ---------------------------------------------------------------------------
# Cache (Redis)
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("CACHE_URL", default="redis://redis:6379/2"),
    },
}


# ---------------------------------------------------------------------------
# Email (Gmail SMTP)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = config(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("GMAIL_USER", default="")
EMAIL_HOST_PASSWORD = config("GMAIL_APP_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER or "noreply@example.com")


# ---------------------------------------------------------------------------
# Allegro API
# ---------------------------------------------------------------------------

ALLEGRO_CLIENT_ID = config("ALLEGRO_CLIENT_ID", default="")
ALLEGRO_CLIENT_SECRET = config("ALLEGRO_CLIENT_SECRET", default="")
ALLEGRO_API_BASE_URL = config("ALLEGRO_API_BASE_URL", default="https://api.allegro.pl")
ALLEGRO_AUTH_URL = config("ALLEGRO_AUTH_URL", default="https://allegro.pl/auth/oauth/token")


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Warsaw"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
