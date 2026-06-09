# CLAUDE.md — instrukcja dla Claude'a kontynuującego projekt

Plik dla Claude'a, który dołącza do projektu na innym komputerze po `git pull`. Człowiek-użytkownik (Jakub) jest polskim studentem PZSI 2025, pracuje na laptopie z Dockerem.

---

## 1. Co to za projekt

**Price History Scanner** — multi-platformowy tracker cen (Allegro + Amazon) dla laboratorium PZSI 2025 (Projektowanie zaawansowanych systemów informatycznych). Główne wymagania merytoryczne:

- Cross-platform groups (jeden produkt = oferty na kilku platformach)
- Smart polling przez Coefficient of Variation
- Wykrywanie flash sales przez Z-score
- TimescaleDB hypertable na historię cen
- Celery multi-queue (wysoki_priorytet, niski_priorytet, powiadomienia)
- JWT auth
- Email alerts przez Gmail SMTP

Pełna dokumentacja w `docs/` (PL): api, architektura, baza-danych, scrapery, zadania-w-tle, analityka.

---

## 2. Stack

- **Backend**: Django 5.1 + DRF + simplejwt + drf-spectacular + django-filter + django-cors-headers
- **Bazy**: PostgreSQL 15 (default, transakcyjna) + TimescaleDB latest-pg15 (timeseries, port 5433)
- **Cache/broker**: Redis 7
- **Task queue**: Celery 5 z trzema kolejkami i Beat
- **Analityka**: pandas + numpy
- **Scrapery**: requests + `responses` (mock w testach); Amazon = Playwright (jeszcze nie zaimplementowane)
- **Frontend**: Vite + React 18 + TS + Tailwind v4 + Recharts + react-router-dom + axios
- **Package manager**: `uv` (backend), `npm` (frontend)
- **Lint/format/typy**: ruff + mypy (backend), tsc (frontend)
- **Testy**: pytest + pytest-django + responses + factory-boy (138 testów backend)
- **Pre-commit**: ruff + standardowe hooki

---

## 3. Co już zrobiliśmy (Phases 0–9, wszystko zacommitowane)

| Phase | Co | Pliki kluczowe |
|-------|-----|----------------|
| 0 | Scaffold (django-admin, settings, multi-DB router, Celery app, smoke tests) | `backend/config/`, `docker-compose.yml`, `Makefile`, `pyproject.toml` |
| 1 | JWT auth (register/login/refresh/me) | `backend/users/` |
| 2 | Domain core: Platforma, Sprzedawca, Produkt, GrupaProduktow + groups CRUD | `backend/groups/`, `backend/products/models.py`, `backend/sellers/`, seed migration |
| 3 | TimescaleDB hypertable `historia_cen` + `HistoriaCenRepository` | `backend/analytics/repositories.py`, `analytics/migrations/0001_initial.py` (RunSQL) |
| 4 | URL detector + AllegroAuthClient + AllegroClient + AmazonScraper stub | `backend/scrapers/detection.py`, `scrapers/allegro.py`, `scrapers/amazon.py`, `scrapers/base.py` |
| 5 | Celery `fetch_product_price` + `POST /api/groups/{id}/products/` | `backend/scrapers/tasks.py`, `backend/products/views.py` |
| 6 | VolatilityCalculator (CV) + AnomalyDetector (Z-score) + smart polling cadence | `backend/analytics/services.py`, `analytics/tasks.py` |
| 7 | Alert model + email task + trigger w `update_product_cache` | `backend/alerts/` |
| 8 | Throttling + refresh/prices/comparison/delete endpoints + drf-spectacular polish | `backend/groups/views.py` (actions), `backend/config/settings.py` |
| 9 | React SPA: login, register, dashboard, group detail (z Recharts), alerts | `frontend/src/` |

**Stan testów**: 138 backend testów zielonych, ruff clean, mypy clean (`uv run pytest && uv run ruff check . && uv run mypy users/ config/ groups/ products/ sellers/ analytics/ scrapers/ alerts/`).

**Stan integracji**: Gmail SMTP zweryfikowany działa (`send_mail` zwraca 1, mail dochodzi). Allegro API czeka na akceptację.

---

## 4. Co zostało do zrobienia

### Blokujące uruchomienie

1. **Allegro API credentials** — Jakub czeka na akceptację apki na https://apps.developer.allegro.pl/. Po dostaniu credentials wpisuje do `.env`: `ALLEGRO_CLIENT_ID`, `ALLEGRO_CLIENT_SECRET`. Potem `docker compose up -d --force-recreate backend worker-high worker-low worker-notifications beat` (`restart` NIE wczytuje ponownie `.env`!).

### Niezaimplementowane

2. **Amazon scraper Playwright** — `backend/scrapers/amazon.py` to stub rzucający `NotImplementedError`. Implementacja wymaga dodania `playwright` do `pyproject.toml`, instalacji `chromium` w Dockerfile, napisania logiki scrapowania strony produktu (cena, ASIN, sprzedawcy z "Other sellers"). Ryzyko: Amazon agresywnie blokuje boty.

3. **Celery Beat schedule** — kontener `beat` chodzi, ale `app.conf.beat_schedule` jest puste w `config/celery.py`. Trzeba dodać:
   - `fetch_volatile_products` co 15 min (volatility > 0.6) → `wysoki_priorytet`
   - `fetch_stable_products` co 1h (volatility < 0.4) → `niski_priorytet`
   - `cleanup_old_data` co 24h → `niski_priorytet`
   
   Implementacja: nowy task `scrapers.tasks.fetch_due_products()` który robi `Produkt.objects.filter(aktywny=True, nastepne_sprawdzenie__lte=now())` i każdego enqueue'uje na `fetch_product_price`.

### Nice-to-have

4. **Frontend polish** — toasty zamiast `alert()` i `confirm()`, loading spinners, error boundary, mobile responsiveness przy `<sm`.
5. **Endpointy z docs niezrobione**: `GET /api/products/{id}/prices/`, `GET /api/products/{id}/sellers/`, `GET /api/groups/{id}/stats/`, `GET /api/groups/{id}/anomalies/` — można dodać jak frontend będzie ich potrzebować.
6. **Real end-to-end test** — gdy Allegro creds przyjdą: zarejestruj się, utwórz grupę, wklej URL Allegro, sprawdź czy worker zapisał historię, wykres w UI się pojawia, alert się wyzwala.

---

## 5. Konwencje i preferencje użytkownika

Wszystkie poniższe wynikają z bezpośrednich instrukcji Jakuba — **nie odstępuj**:

- **TDD** — najpierw test (red), potem implementacja (green), potem refactor.
- **OOP + clean code** — klasy nad funkcjami przy złożoności, jawne typy, dependency injection (np. `VolatilityCalculator(repo)`).
- **Docker-compose dla całego stacka** — żadnych instalacji na hoście. Wszystko przez `docker compose exec backend uv run ...`.
- **Backend przed frontendem** — backend skończony, frontend jest MVP.
- **Dokumentacja po polsku** (`.md`, README, ten plik) — komentarze w kodzie mogą być po angielsku.
- **Django CLI dla scaffoldingu** — `django-admin startproject`, `manage.py startapp <name>`, `manage.py makemigrations`. Nie pisz boilerplatu ręcznie.
- **Polskie nazwy w domenie/DB** — tabele: `uzytkownicy`, `grupy_produktow`, `produkty`, `platformy`, `sprzedawcy`, `alerty`, `historia_cen`. Modele Django mają polskie nazwy (`Produkt`, `GrupaProduktow`, `Sprzedawca`, `Platforma`, `Alert`, `HistoriaCen`). Pola też po polsku (`nazwa`, `cena_docelowa`, `wskaznik_zmiennosci`, `najlepsza_platforma`).
- **Krótkie odpowiedzi** — Jakub czyta diffy i kod, nie potrzebuje rozwlekłych streszczeń po każdym commicie.

---

## 6. Jak uruchomić projekt na nowym komputerze

```bash
# 1. Zainstaluj Docker Desktop + włącz WSL2 integration (jeśli Windows)
# 2. Sklonuj repo
git clone <repo-url>
cd price_history_scanner

# 3. Skopiuj .env.example -> .env i uzupełnij credentials
cp .env.example .env
# edytuj: GMAIL_USER, GMAIL_APP_PASSWORD, ALLEGRO_CLIENT_ID, ALLEGRO_CLIENT_SECRET

# 4. Postaw stack
docker compose up -d --build

# 5. Pierwszy raz: zsynchronizuj uv venv w kontenerze (z dev + test groups)
docker compose exec backend uv sync --group test --group dev

# 6. Migruj obie bazy (default + timeseries)
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py migrate --database=timeseries

# 7. Uruchom testy żeby potwierdzić zielony stan
docker compose exec backend uv run pytest

# 8. Otwórz frontend
# http://localhost:5173

# 9. (Opcjonalnie) Swagger UI
# http://localhost:8000/api/docs/
```

`Makefile` w repo root ma alias na większość: `make up`, `make migrate`, `make test`, `make lint`, `make format`, `make typecheck`, `make check` (= lint + typecheck + test).

---

## 7. Kluczowe gotchas (z mojej pamięci sesji)

1. **`docker compose restart` NIE wczytuje ponownie `.env`** — trzeba `up -d --force-recreate`.
2. **TimescaleDB hypertable bypassuje ORM** — `historia_cen` nie ma `id` PK (TimescaleDB wymaga klucza zawierającego kolumnę czasową). Pisz/czytaj zawsze przez `HistoriaCenRepository` (raw SQL), nie przez ORM. Model `HistoriaCen` jest `managed=False`.
3. **DB router działa per-app**, nie per-model — `TIMESERIES_APPS = {"analytics"}` w `config/routers.py`. Model-based routing nie działało dla `RunSQL` migracji (brak `model_name`).
4. **`TEST.DEPENDENCIES = []`** na bazie `timeseries` jest konieczne — bez tego Django wykrywa "circular dependency" przy setupie testów.
5. **W testach Celery jest EAGER** (`conftest.py` w root), email = `locmem`, cache jest czyszczony przed/po każdym teście (throttle counters). Te trzy fixture są autouse.
6. **`update_group_cache` wywołujemy SYNCHRONICZNIE** w `fetch_product_price` przed `update_product_cache.delay(...)`, bo `update_product_cache` ewaluuje alerty na podstawie `grupa.najnizsza_cena_globalna`.
7. **AnomalyDetector i VolatilityCalculator przyjmują `now=` parametr** — pamiętaj o przekazywaniu w testach z seedowanymi datami, żeby okno 30d/14d obejmowało dane.
8. **`Decimal` jest serializowany jako float** w surowym `Response({...})` — w endpointach `prices`/`comparison` używam `str(decimal)` żeby zachować precyzję groszy.
9. **DRF throttle nie obsługuje "5/15m"** — tylko sufiksy s/m/h/d. Login mamy `5/min` (ostrzejsze niż docs, ale ważne że throttluje).
10. **uv venv mountuje się jako volume** — gdy zmieniasz `pyproject.toml`, zrób `docker compose exec backend uv sync --group test --group dev`. Po dodaniu zależności i restarcie kontenera czasem trzeba `--force-recreate`.

---

## 8. Co już istnieje w `~/.claude/projects/...memory/` (na maszynie Jakuba, NIE w repo)

Mam zapisane:
- profil użytkownika
- preferencje TDD, OOP, Docker, backend-first
- polskie nazewnictwo w domenie
- konwencja polskich docs / angielskich komentarzy
- używanie CLI Django
- wskaźnik na `docs/` jako źródło prawdy o architekturze

Na nowym komputerze tej pamięci nie będzie — CLAUDE.md (ten plik) ma ją zastąpić. Jeśli czegoś brakuje, zapytaj Jakuba i potem zaktualizuj ten plik **commitem do repo**, żeby przeniosło się na kolejne maszyny.

---

## 9. Następny krok jeśli Allegro przyszło

1. Wpisz creds do `.env`, `docker compose up -d --force-recreate backend worker-high worker-low worker-notifications beat`
2. Przez UI dodaj grupę i wklej URL produktu z Allegro
3. Obserwuj logi `worker-high`: `docker compose logs -f worker-high` — powinno polecieć fetchowanie ofert, zapis do TimescaleDB
4. Wykres na detail page powinien pokazać kropki cen
5. Jak działa — zacommituj `.env.example` z notatką "wymagane: zarejestruj apkę na apps.developer.allegro.pl"
6. Wtedy bierzemy się za Beat schedule albo Amazon Playwright

Jeśli pojawi się 401 z Allegro: token może być zacheszowany w Redis — `docker compose exec backend uv run python manage.py shell -c "from django.core.cache import cache; cache.delete('allegro:access_token')"` i spróbuj znowu.
