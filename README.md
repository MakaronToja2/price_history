# Price History Scanner

Aplikacja do monitorowania cen produktów w wielu sklepach internetowych — projekt z przedmiotu **PZSI 2025** (Projektowanie zaawansowanych systemów informatycznych).

System śledzi ceny produktów na platformach **Allegro** i **Amazon**, monitoruje wszystkich sprzedawców na każdej platformie, automatycznie wykrywa flash sales za pomocą Z-score oraz powiadamia użytkowników mailowo.

Pełna specyfikacja architektoniczna znajduje się w katalogu [`docs/`](./docs/).

## Stos technologiczny

- **Backend**: Django 5 + DRF + SimpleJWT, Celery 5 + Redis, Pandas/NumPy
- **Bazy danych**: PostgreSQL 15 (dane transakcyjne) + TimescaleDB (szeregi czasowe, port 5433)
- **Pozyskiwanie danych**: Allegro REST API (OAuth2), Amazon przez Playwright
- **Frontend** (Faza 9): React 18 + TypeScript + TailwindCSS + Recharts
- **Narzędzia**: uv, ruff, mypy, pytest, pre-commit, docker-compose

## Szybki start

```bash
cp .env.example .env             # uzupełnij sekrety
make build                       # zbuduj obrazy Dockera
make up                          # uruchom stos
make migrate                     # zastosuj migracje
make test                        # uruchom testy
```

Dokumentacja API (Swagger UI) będzie dostępna pod adresem
<http://localhost:8000/api/docs/> po ukończeniu Fazy 1.

## Najczęstsze polecenia

```bash
make logs           # podgląd logów wszystkich usług
make shell          # powłoka Django (shell_plus)
make lint           # ruff check (analiza statyczna)
make format         # ruff format + autofix
make typecheck      # mypy (sprawdzanie typów)
make check          # lint + typecheck + test
make clean          # zatrzymanie z usunięciem woluminów
```

## Fazy implementacji

Projekt jest budowany w podejściu **backend-first**, zgodnie z metodyką **TDD**.
Każda faza kończy się zielonym build'em (testy, lint i typy przechodzą) zanim
rozpocznie się następna.

| Faza | Zakres |
|------|--------|
| 0 | Szkielet projektu (docker-compose, konfiguracje, pusty Django) |
| 1 | Autoryzacja JWT (rejestracja, logowanie, refresh) |
| 2 | Modele domenowe: grupy produktów, produkty, sprzedawcy, platformy |
| 3 | Warstwa TimescaleDB (hypertabela `historia_cen`) |
| 4 | Klienty platform: Allegro API i scraper Amazon (Playwright) |
| 5 | Celery — multi-queue, retry, idempotentność, harmonogram |
| 6 | Analityka: wskaźnik zmienności (CV), detekcja anomalii (Z-score) |
| 7 | Alerty cenowe i wysyłka powiadomień email (Gmail SMTP) |
| 8 | Polerowanie API (paginacja, throttling, OpenAPI) |
| 9 | Frontend (React + TS) |

## Uruchamianie bez Dockera (opcjonalnie)

```bash
cd backend
uv sync --all-groups
uv run python manage.py migrate
uv run pytest
```

Wymagane: zainstalowane `uv` lokalnie oraz dostępne usługi PostgreSQL i Redis
(zaleca się uruchomienie ich przez docker-compose nawet gdy Django działa
na hoście).

## Struktura repozytorium

```
.
├── docs/                       # specyfikacja projektu (po polsku)
├── backend/                    # kod backendu (Django + Celery)
│   ├── config/                 # ustawienia Django, Celery, routery DB
│   ├── apps/                   # aplikacje Django (users, groups, ...)
│   └── tests/                  # testy ogólnoprojektowe
├── frontend/                   # (Faza 9) aplikacja React
├── docker-compose.yml          # cała infrastruktura
├── Makefile                    # skróty dla typowych operacji
└── .pre-commit-config.yaml     # hooki formatujące/lintujące
```
