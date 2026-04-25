# Architektura Celery (Multi-Queue)

## 1. Wprowadzenie

System Price History wykorzystuje **Celery** z **Redis** jako brokerem do obsługi zadań w tle. Architektura oparta jest na **wielu kolejkach** (multi-queue) - różne typy zadań trafiają do różnych kolejek o różnych priorytetach.

**Cel:** Niezawodne, skalowalne wykonywanie zadań asynchronicznych:
- Pobieranie cen z Allegro/Amazon
- Aktualizacja statystyk
- Wysyłka emaili z alertami
- Detekcja anomalii

---

## 2. Diagram architektury

```mermaid
graph TB
    subgraph Backend
        DjangoApp[Django App]
        APIView[API Views]
    end

    subgraph CeleryBeat["Celery Beat (Scheduler)"]
        Schedule["Cron-like schedule:<br/>- co 15 min: volatile products<br/>- co 1h: stable products<br/>- co 24h: cleanup"]
    end

    subgraph Redis
        Q1["Kolejka:<br/>wysoki_priorytet"]
        Q2["Kolejka:<br/>niski_priorytet"]
        Q3["Kolejka:<br/>powiadomienia"]
    end

    subgraph Workers["Celery Workers"]
        W1["Worker 1<br/>queues: wysoki_priorytet<br/>concurrency: 4"]
        W2["Worker 2<br/>queues: niski_priorytet<br/>concurrency: 2"]
        W3["Worker 3<br/>queues: powiadomienia<br/>concurrency: 4"]
    end

    DjangoApp -->|task.delay()| Q1
    DjangoApp -->|task.delay()| Q3
    APIView -->|refresh task| Q1
    Schedule -->|scheduled tasks| Q1
    Schedule -->|scheduled tasks| Q2

    Q1 --> W1
    Q2 --> W2
    Q3 --> W3
```

---

## 3. Kolejki

### 3.1 Definicje kolejek

| Kolejka | Cel | Priority | Concurrency |
|---------|-----|----------|-------------|
| `wysoki_priorytet` | Sprawdzanie zmiennych produktów (volatility >= 0.6), force refresh | Wysoki | 4 |
| `niski_priorytet` | Sprawdzanie stabilnych produktów (volatility < 0.6), aktualizacja statystyk | Niski | 2 |
| `powiadomienia` | Wysyłka emaili, push notifications | Średni | 4 |

### 3.2 Konfiguracja w Django

```python
# config/celery.py
from celery import Celery
from kombu import Queue

app = Celery('price_history')

app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/1',

    task_queues=(
        Queue('wysoki_priorytet', routing_key='wysoki.#'),
        Queue('niski_priorytet', routing_key='niski.#'),
        Queue('powiadomienia', routing_key='powiadomienie.#'),
    ),
    task_default_queue='niski_priorytet',
    task_default_routing_key='niski.default',

    task_routes={
        'tasks.fetch_volatile_products': {'queue': 'wysoki_priorytet'},
        'tasks.fetch_product_price': {'queue': 'wysoki_priorytet'},
        'tasks.fetch_stable_products': {'queue': 'niski_priorytet'},
        'tasks.update_statistics': {'queue': 'niski_priorytet'},
        'tasks.send_alert_email': {'queue': 'powiadomienia'},
    },

    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    timezone='Europe/Warsaw',
    enable_utc=True,

    task_track_started=True,
    task_time_limit=600,  # 10 min hard limit
    task_soft_time_limit=540,  # 9 min soft limit
)
```

### 3.3 Auto-discovery zadań

```python
app.autodiscover_tasks([
    'users',
    'products',
    'alerts',
    'analytics',
    'scrapers',
])
```

---

## 4. Workery

### 4.1 Uruchamianie workerów

System uruchamia **3 osobne workery**, każdy obsługujący inne kolejki:

```bash
# Terminal 1: Wysoki priorytet (sprawdzanie zmiennych)
celery -A config worker -Q wysoki_priorytet -l info -c 4 -n worker_high@%h

# Terminal 2: Niski priorytet (sprawdzanie stabilnych, statystyki)
celery -A config worker -Q niski_priorytet -l info -c 2 -n worker_low@%h

# Terminal 3: Powiadomienia
celery -A config worker -Q powiadomienia -l info -c 4 -n worker_notif@%h

# Terminal 4: Beat scheduler
celery -A config beat -l info
```

### 4.2 Dlaczego osobne workery?

**Zalety:**
- Wysokopriorytetowe zadania nie są blokowane przez długie statystyki
- Email task się nie zatrzymuje, nawet gdy scrapery są przeciążone
- Skalowanie horyzontalne - więcej workerów wysokiego priorytetu w godzinach szczytu

### 4.3 Concurrency model

Domyślnie Celery używa **prefork** (osobne procesy):

```bash
celery -A config worker --pool=prefork -c 4
```

**Alternatywy:**
| Pool | Przypadek użycia |
|------|------------------|
| `prefork` | Domyślny, CPU-bound tasks |
| `gevent` | I/O-bound (np. wiele HTTP requestów) - lekki async |
| `threads` | Mixed |

**Dla scraperów (Playwright):** używamy `prefork` (Playwright sam zarządza async eventloop wewnętrznie).

**Dla emaili:** można użyć `gevent` dla efektywnego I/O.

---

## 5. Definicje zadań

### 5.1 Struktura zadania

```python
# tasks/price_tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    autoretry_for=(requests.RequestException, TimeoutError),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def fetch_product_price(self, product_id: int):
    """
    Fetch current prices for all sellers of a product.

    Routed to: wysoki_priorytet
    Triggered by: scheduled tasks, API force-refresh
    """
    logger.info(f"Fetching prices for product {product_id}")

    product = Product.objects.get(id=product_id)

    # Wybierz scraper based on platforma
    if product.platforma.nazwa == 'allegro':
        scraper = AllegroClient(auth_client)
        offers = scraper.get_product_offers(product.zewnetrzny_id)
    elif product.platforma.nazwa == 'amazon':
        scraper = AmazonScraper()
        offers = asyncio.run(scraper.scrape_product(product.zewnetrzny_id))
    else:
        raise ValueError(f"Unknown platform: {product.platforma.nazwa}")

    # Zapisz w TimescaleDB
    save_price_records(product, offers)

    # Update cache w produkty + grupy_produktow
    update_product_cache.delay(product_id)

    # Detekcja anomalii
    detect_and_alert.delay(product_id)
```

### 5.2 Lista wszystkich zadań

| Zadanie | Kolejka | Trigger | Opis |
|---------|---------|---------|------|
| `fetch_product_price(product_id)` | wysoki | Scheduled, API | Pobiera ceny dla 1 produktu |
| `fetch_volatile_products()` | wysoki | Beat (15 min) | Triggeruje fetch_product_price dla wszystkich volatile |
| `fetch_stable_products()` | niski | Beat (1h) | Triggeruje fetch_product_price dla stable |
| `update_product_cache(product_id)` | niski | After fetch | Aktualizuje statystyki w produkty |
| `update_group_cache(group_id)` | niski | After cache update | Aktualizuje cross-platform best price |
| `detect_and_alert(product_id)` | niski | After fetch | Detekcja anomalii + trigger alertów |
| `send_alert_email(alert_id, ...)` | powiadomienia | Anomaly detected | Wysyła email |
| `cleanup_old_data()` | niski | Beat (24h) | Usuwa stare logi błędów |

---

## 6. Celery Beat (Scheduler)

### 6.1 Konfiguracja schedule

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'fetch-volatile-products': {
        'task': 'tasks.fetch_volatile_products',
        'schedule': crontab(minute='*/15'),  # co 15 min
        'options': {'queue': 'wysoki_priorytet'}
    },
    'fetch-stable-products': {
        'task': 'tasks.fetch_stable_products',
        'schedule': crontab(minute=0),  # co godzinę o pełnej godzinie
        'options': {'queue': 'niski_priorytet'}
    },
    'cleanup-old-data': {
        'task': 'tasks.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0),  # codziennie o 3:00
        'options': {'queue': 'niski_priorytet'}
    },
}
```

### 6.2 Storage scheduler

Domyślnie Celery Beat zapisuje state w pliku `celerybeat-schedule`. W produkcji można użyć `django-celery-beat` (zapisywanie w bazie):

```bash
pip install django-celery-beat
```

```python
INSTALLED_APPS = [..., 'django_celery_beat']

# Uruchamianie:
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## 7. Retry strategy

### 7.1 Domyślna konfiguracja

```python
@shared_task(
    autoretry_for=(Exception,),  # retry on any exception (zwykle za szerokie)
    retry_kwargs={
        'max_retries': 3,
        'countdown': 60,  # początkowy delay
    },
    retry_backoff=True,        # exponential backoff
    retry_backoff_max=600,      # max 10 min między próbami
    retry_jitter=True,          # +/- 25% jitter (rozprasza retry)
)
def my_task():
    ...
```

### 7.2 Selektywny retry

Lepiej retry tylko dla specific exceptions:

```python
@shared_task(
    autoretry_for=(
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        TimeoutError,
    ),
    # NIE retry dla: ValueError, KeyError, ProductNotFound (404)
)
def fetch_with_smart_retry():
    ...
```

### 7.3 Manual retry

Dla custom logiki:

```python
@shared_task(bind=True, max_retries=5)
def fetch_with_rate_limit(self, product_id):
    try:
        return fetch_data(product_id)
    except RateLimitException:
        # Czekaj dłużej przy rate limit
        raise self.retry(countdown=300)  # 5 min
    except CaptchaException:
        # CAPTCHA - czekaj 1h, zmień User-Agent
        raise self.retry(countdown=3600)
```

---

## 8. Idempotentność

Zadania powinny być **idempotentne** - można je powtórzyć bez efektów ubocznych:

### 8.1 Anti-pattern (zły)

```python
@shared_task
def increment_counter(product_id):
    product = Product.objects.get(id=product_id)
    product.fetch_count += 1
    product.save()
    # Jeśli task się retry-uje, counter zwiększy się 2x!
```

### 8.2 Pattern (dobry)

```python
@shared_task
def fetch_and_save_price(product_id, fetch_id):
    # fetch_id = unique ID każdego fetch
    if PriceRecord.objects.filter(fetch_id=fetch_id).exists():
        return  # Już zapisane - skip

    fetch_price_and_save(product_id, fetch_id)
```

### 8.3 Lock-based idempotency

Dla zadań typu "scheduled fetch":

```python
@shared_task
def fetch_product_price(product_id):
    lock_key = f"fetch_lock:{product_id}"

    # Tylko jeden task fetch-uje produkt jednocześnie
    if not redis.set(lock_key, "1", nx=True, ex=60):
        logger.info(f"Fetch already in progress for product {product_id}")
        return

    try:
        do_fetch(product_id)
    finally:
        redis.delete(lock_key)
```

---

## 9. Monitorowanie

### 9.1 Flower (web UI)

```bash
pip install flower
celery -A config flower --port=5555

# Otwórz: http://localhost:5555
```

Pokazuje:
- Aktywne workery
- Tasks per minute/hour/day
- Failed tasks
- Queue lengths
- Task results

### 9.2 Logging

```python
# settings.py
LOGGING = {
    'loggers': {
        'celery': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
        },
        'celery.task': {
            'level': 'INFO',
            'handlers': ['file'],
        },
    },
}
```

### 9.3 Kluczowe metryki

| Metryka | Cel | Próg alarmu |
|---------|-----|-------------|
| Task throughput | >100/min | <10/min |
| Failed task rate | <5% | >20% |
| Queue length | <100 | >1000 (saturated) |
| Avg execution time | <30s | >60s |
| Worker uptime | >99% | <95% |

---

## 10. Tworzenie tasków - best practices

### 10.1 Małe, atomowe zadania

❌ **Źle:**
```python
@shared_task
def do_everything():
    fetch_all_products()       # 30 min
    update_all_statistics()    # 20 min
    send_all_emails()          # 10 min
```

✅ **Dobrze:**
```python
@shared_task
def fetch_product_price(product_id):  # ~10 sec
    ...

@shared_task
def update_statistics(product_id):  # ~1 sec
    ...

@shared_task
def send_email(alert_id):  # ~2 sec
    ...
```

### 10.2 Pass IDs, not objects

❌ **Źle:**
```python
@shared_task
def process_product(product):  # Serializacja całego objektu!
    ...

# Wywołanie:
process_product.delay(Product.objects.get(id=1))
```

✅ **Dobrze:**
```python
@shared_task
def process_product(product_id):
    product = Product.objects.get(id=product_id)
    ...

process_product.delay(1)
```

### 10.3 Use chains and groups

```python
from celery import chain, group

# Sequential: A → B → C
chain(
    fetch_product_price.s(product_id),
    update_statistics.s(),
    detect_anomaly.s()
).apply_async()

# Parallel: fetch wszystkich produktów w grupie
group([
    fetch_product_price.s(p.id) for p in products
]).apply_async()
```

---

## 11. Skalowanie

### 11.1 Vertical (więcej workerów)

```bash
# Zwiększ concurrency:
celery -A config worker -c 16

# Albo uruchom więcej workerów:
celery -A config worker -n worker1@host
celery -A config worker -n worker2@host
```

### 11.2 Horizontal (na wielu serwerach)

Celery wspiera distributed workers natywnie:
- Każdy serwer uruchamia worker connecting do tego samego Redis
- Zadania automatycznie rozkładają się na workery

### 11.3 Priorytetyzacja

W obrębie kolejki można użyć priority queues (Redis 6+ z `kombu` priority):

```python
fetch_product_price.apply_async(
    args=[product_id],
    queue='wysoki_priorytet',
    priority=10  # 0-10, 10 = highest
)
```

---

## 12. Powiązane dokumenty

- [Smart Polling - harmonogramowanie](smart-polling.md)
- [Definicje wszystkich tasków](definicje-taskow.md)
- [Wskaźnik zmienności](../analityka/wskaznik-zmiennosci.md)
- [Allegro API](../scrapery/allegro-api.md)
- [Amazon scraper](../scrapery/amazon-scraper.md)
