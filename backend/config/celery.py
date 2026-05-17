"""Celery application configuration.

Implements the multi-queue setup described in
`docs/zadania-w-tle/architektura-celery.md`.
"""

import os

from celery import Celery
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("price_history")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Three queues with different priorities; workers are pinned to specific queues
# in docker-compose.yml.
app.conf.task_queues = (
    Queue("wysoki_priorytet", routing_key="wysoki.#"),
    Queue("niski_priorytet", routing_key="niski.#"),
    Queue("powiadomienia", routing_key="powiadomienie.#"),
)
app.conf.task_default_queue = "niski_priorytet"
app.conf.task_default_routing_key = "niski.default"

# Per-task routing is added as tasks land in later phases.
app.conf.task_routes = {}

app.autodiscover_tasks()
