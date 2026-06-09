"""Database router: send the analytics app's models to TimescaleDB."""

from typing import Any

# Apps whose data lives in TimescaleDB.
TIMESERIES_APPS: set[str] = {"analytics"}


class PriceHistoryRouter:
    """Routes reads/writes/migrations between PostgreSQL and TimescaleDB."""

    def db_for_read(self, model: Any, **hints: Any) -> str | None:
        if model._meta.app_label in TIMESERIES_APPS:
            return "timeseries"
        return "default"

    def db_for_write(self, model: Any, **hints: Any) -> str | None:
        if model._meta.app_label in TIMESERIES_APPS:
            return "timeseries"
        return "default"

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool | None:
        return None

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: Any,
    ) -> bool | None:
        if db == "timeseries":
            return app_label in TIMESERIES_APPS
        return app_label not in TIMESERIES_APPS
