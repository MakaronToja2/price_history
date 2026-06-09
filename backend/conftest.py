"""Project-wide pytest configuration.

Forces Celery into eager (synchronous) mode for all tests so chained
`.delay()` calls execute inline and assertions can observe their side
effects without a real broker/worker.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _celery_eager(settings) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture(autouse=True)
def _locmem_email(settings) -> None:
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def _reset_throttles() -> None:
    """DRF stores throttle counters in Django's cache; clear it so per-test
    request volumes don't trip rate limits set in settings."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
