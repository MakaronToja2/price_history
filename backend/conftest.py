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
