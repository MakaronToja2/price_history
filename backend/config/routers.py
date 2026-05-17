"""Database router: send time-series models to the `timeseries` DB."""

from typing import Any

# Names of models whose data lives in TimescaleDB. Populated when the
# `historia_cen` hypertable model lands in Phase 3.
TIMESERIES_MODELS: set[str] = set()


class PriceHistoryRouter:
    """Routes reads/writes/migrations between PostgreSQL and TimescaleDB."""

    def db_for_read(self, model: Any, **hints: Any) -> str | None:
        if model._meta.model_name in TIMESERIES_MODELS:
            return "timeseries"
        return "default"

    def db_for_write(self, model: Any, **hints: Any) -> str | None:
        if model._meta.model_name in TIMESERIES_MODELS:
            return "timeseries"
        return "default"

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool | None:
        # Cross-database relations are not supported here; let Django decide.
        return None

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: Any,
    ) -> bool | None:
        is_timeseries = (model_name in TIMESERIES_MODELS) if model_name else False
        if db == "timeseries":
            return is_timeseries
        return not is_timeseries
