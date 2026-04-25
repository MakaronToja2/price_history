# Diagram Komponentów

## 1. Wprowadzenie

Dokument przedstawia szczegółowy diagram komponentów systemu Price History wraz z opisem interakcji między nimi. System składa się z czterech głównych warstw: prezentacji (frontend), aplikacji (backend), zadań w tle (workers) oraz warstwy danych (bazy danych).

---

## 2. Pełny diagram architektury

```mermaid
graph TB
    subgraph Frontend["WARSTWA PREZENTACJI"]
        UI["React + TypeScript SPA<br/>Routing | Auth Context | API Service<br/>Strony: Login, Panel główny, Grupy, Alerty<br/>Komponenty: GroupCard, PlatformComparison, PriceChart"]
    end

    subgraph Backend["WARSTWA APLIKACJI"]
        DRF["Django + DRF<br/>Middleware: JWT Auth, CORS"]
        Apps["Aplikacje Django<br/>users | groups | products<br/>sellers | alerts | analytics"]
        Stats["Silnik Statystyk (Pandas + NumPy)<br/>volatility | anomaly detection<br/>aggregate group prices"]
        DRF --> Apps
        Apps --> Stats
    end

    subgraph DataLayer["WARSTWA DANYCH"]
        PG[("PostgreSQL :5432<br/>uzytkownicy, grupy_produktow,<br/>produkty, sprzedawcy,<br/>platformy, alerty")]
        TS[("TimescaleDB :5433<br/>historia_cen (hypertabela)<br/>dzienna_statystyka_cen<br/>retention: 1 rok")]
    end

    subgraph Workers["WARSTWA ZADAŃ W TLE"]
        Redis[("Redis :6379<br/>Broker + Result Backend<br/>Kolejki: wysoki/niski priorytet,<br/>powiadomienia")]
        Celery["Workery Celery<br/>Allegro Client (OAuth2)<br/>Amazon Scraper (Playwright)<br/>Email Sender (SMTP)<br/>Analytics Runner (Pandas)"]
        Beat["Celery Beat<br/>co 15 min: volatile<br/>co 1h: stable"]
        Beat --> Redis
        Redis <--> Celery
    end

    subgraph External["USŁUGI ZEWNĘTRZNE"]
        Allegro["Allegro REST API<br/>OAuth2 Client Credentials<br/>/sale/products/{id}<br/>/offers/listing"]
        Amazon["Amazon (web)<br/>amazon.pl, amazon.de<br/>Headless Chromium<br/>Buy Box + Other Sellers"]
        Gmail["Gmail SMTP<br/>smtp.gmail.com:587<br/>TLS + App Password"]
    end

    UI -- "REST API + JWT" --> DRF
    Apps -- "ORM" --> PG
    Apps -- "ORM (multi-db router)" --> TS
    Apps -- "delay()" --> Redis
    Celery -- "ORM" --> PG
    Celery -- "ORM" --> TS
    Celery -- "OAuth2 + REST" --> Allegro
    Celery -- "Headless browser" --> Amazon
    Celery -- "SMTP/TLS" --> Gmail
```

---

## 3. Opis komponentów

### 3.1 Warstwa prezentacji (Frontend)

#### React SPA (Single Page Application)
**Odpowiedzialność:** Interfejs użytkownika, zarządzanie stanem, komunikacja z API

**Kluczowe komponenty:**
- **Router** - nawigacja między stronami (React Router)
- **Auth Context** - zarządzanie tokenami JWT, stan zalogowania
- **API Service** - centralna warstwa komunikacji z backendem (Axios)
- **Strony** - widoki aplikacji (Login, Panel główny, Szczegóły grupy, Alerty)
- **Komponenty wielokrotnego użytku** - GroupCard, PlatformComparison, PriceChart, SellerList

### 3.2 Warstwa aplikacji (Backend)

#### Django + DRF
**Odpowiedzialność:** Logika biznesowa, REST API, uwierzytelnianie

**Aplikacje Django:**

| Aplikacja | Odpowiedzialność |
|-----------|------------------|
| `users` | Rejestracja, logowanie, JWT, profil |
| `groups` | Grupy produktów (cross-platform) |
| `products` | Produkty per platforma w grupie |
| `sellers` | Sprzedawcy odkryci podczas scrapowania |
| `alerts` | Alerty cenowe (na poziomie grupy) |
| `analytics` | Endpointy statystyczne |

#### Silnik Statystyk
**Odpowiedzialność:** Obliczenia analityczne, wykrywanie anomalii

**Funkcje:**
- `calculate_volatility_score()` - oblicza wskaźnik zmienności (CV)
- `update_product_statistics()` - aktualizuje cache statystyk produktu
- `detect_anomaly()` - wykrywa flash sale na podstawie Z-score
- `get_check_interval()` - mapuje volatility na interwał sprawdzania
- `aggregate_group_prices()` - znajduje najniższą cenę cross-platform

### 3.3 Warstwa zadań w tle (Workers)

#### Celery
**Odpowiedzialność:** Asynchroniczne zadania, cykliczne sprawdzanie cen

**Multi-queue architecture:**

| Kolejka | Zadania | Częstotliwość |
|---------|---------|---------------|
| `wysoki_priorytet` | Sprawdzanie produktów zmiennych | Co 15 min |
| `niski_priorytet` | Sprawdzanie produktów stabilnych | Co 1-24h |
| `powiadomienia` | Wysyłka emaili | Natychmiast |

**Workery:**
- **Allegro Client** - OAuth2, pobieranie wszystkich ofert produktu
- **Amazon Scraper** - Playwright, scraping Buy Box + Other Sellers
- **Email Sender** - wysyłka powiadomień przez Gmail SMTP
- **Analytics Runner** - obliczenia Pandas po każdym fetch

#### Celery Beat
**Odpowiedzialność:** Harmonogramowanie cyklicznych zadań

### 3.4 Warstwa danych

#### PostgreSQL
**Odpowiedzialność:** Dane transakcyjne (relacyjne)

**Tabele:**
- `uzytkownicy` - konta użytkowników
- `grupy_produktow` - grupy do cross-platform comparison
- `produkty` - produkty per platforma w grupie
- `sprzedawcy` - sprzedawcy odkryci podczas scrapowania
- `platformy` - dostępne platformy (Allegro, Amazon)
- `alerty` - alerty użytkownika

#### TimescaleDB
**Odpowiedzialność:** Szeregi czasowe (historia cen)

**Hypertabele:**
- `historia_cen` - wszystkie ceny ze wszystkich sprzedawców
  - Flag `jest_najnizsza` dla najniższej ceny w danym timestamp
  - Indeks specjalny dla najniższych cen

**Materialized views:**
- `dzienna_statystyka_cen` - agregaty dzienne (continuous aggregate)

#### Redis
**Odpowiedzialność:** Message broker dla Celery

**Zastosowanie:**
- Kolejki zadań (multi-queue)
- Result backend (wyniki zadań)
- Możliwość rozszerzenia o cache (przyszłość)

---

## 4. Przepływy komunikacji

### 4.1 Dodawanie produktu do grupy

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend as Backend (Django)
    participant Celery as Celery Worker
    participant API as Allegro API / Amazon
    participant PG as PostgreSQL
    participant TS as TimescaleDB

    User->>Frontend: Wkleja URL produktu
    Frontend->>Backend: POST /api/groups/{id}/products/ {url}
    Backend->>Backend: Wykrywa platformę z URL
    Backend->>Backend: Ekstraktuje Product ID / ASIN
    Backend->>PG: INSERT do produkty
    Backend->>Celery: fetch_product_price.delay(id)
    Backend-->>Frontend: 201 Created
    Celery->>API: Pobierz wszystkie oferty/sprzedawców
    API-->>Celery: Lista cen + sprzedawców
    Celery->>TS: INSERT historia_cen (wszystkie ceny)
    Celery->>TS: Flag jest_najnizsza = TRUE dla minimalnej
    Celery->>PG: UPDATE produkty (cache statystyk)
    Celery->>PG: UPDATE grupy_produktow (cross-platform best)
    Celery->>Celery: Sprawdza alerty grupy
    Frontend->>Backend: GET /api/groups/{id}/ (refresh)
    Backend-->>Frontend: Grupa z najniższą ceną
```

### 4.2 Cykliczne sprawdzanie cen (smart polling)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Worker as Celery Worker
    participant PG as PostgreSQL
    participant TS as TimescaleDB
    participant API as External API/Scraper

    Note over Beat: Co 15 min (volatile)<br/>Co 1h (stable)
    Beat->>Worker: check_volatile_products()
    Worker->>PG: SELECT produkty WHERE volatility >= 0.6<br/>AND nastepne_sprawdzenie <= NOW()
    PG-->>Worker: Lista produktów do sprawdzenia
    loop Dla każdego produktu
        Worker->>Worker: fetch_product_price.delay(id)
        Worker->>API: Pobierz ceny
        API-->>Worker: Ceny sprzedawców
        Worker->>TS: INSERT historia_cen
        Worker->>Worker: update_product_statistics()
        Worker->>Worker: detect_anomaly()
        alt Wykryto anomalię (Z-score < -2)
            Worker->>Worker: send_alert_email.delay()
        end
    end
```

### 4.3 Detekcja flash sale

```mermaid
flowchart LR
    A[Nowa cena<br/>z fetch_product_price] --> B[update_product_statistics]
    B --> C{Pobierz 30 dni<br/>z TimescaleDB}
    C --> D[Oblicz średnią,<br/>std, volatility]
    D --> E[Update cache<br/>w produkty]
    E --> F[detect_anomaly]
    F --> G{Z-score < -2?}
    G -->|TAK| H[FLASH SALE detected]
    G -->|NIE| I[Sprawdź<br/>user alerts]
    H --> J[send_alert_email<br/>kolejka: powiadomienia]
    H --> K[UPDATE alerty<br/>ostatnie_wyzwolenie]
    I --> L{Cena <= prog?}
    L -->|TAK| J
    L -->|NIE| M[Koniec]
```

---

## 5. Zewnętrzne zależności

| Usługa | Typ | Cel | Limity |
|--------|-----|-----|--------|
| Allegro REST API | API (OAuth2) | Pobieranie ofert produktu | Rate limit: 9000 req/min |
| Amazon | Web (HTML) | Scraping cen sprzedawców | Anti-bot: rotate UA, delays |
| Gmail SMTP | SMTP | Wysyłka powiadomień email | 500 emaili/dzień (free) |

---

## 6. Skalowalność i rozszerzalność

### 6.1 Dodawanie nowej platformy

Architektura pozwala na łatwe dodanie nowej platformy (np. MediaExpert):

```mermaid
flowchart LR
    A[1. Dodaj rekord<br/>w tabeli platformy] --> B[2. Zaimplementuj<br/>klient/scraper<br/>w backend/scrapers/]
    B --> C[3. Zarejestruj<br/>w URL detector]
    C --> D[4. Dodaj Celery task]
    D --> E[Reszta systemu działa<br/>bez zmian!]
```

Komponenty bez zmian: analityka, alerty, frontend, smart polling, detekcja anomalii.

### 6.2 Skalowanie poziome

- **Wiele workerów Celery** - każdy obsługuje różne kolejki
- **Replikacja PostgreSQL** - read replicas dla analityki
- **TimescaleDB chunking** - automatyczne partycjonowanie po czasie
- **CDN dla frontendu** - statyczne assety

---

## 7. Bezpieczeństwo

### 7.1 Uwierzytelnianie i autoryzacja

- **JWT tokens** - access (15 min) + refresh (7 dni)
- **Hasła** - hashowane przez Django (PBKDF2-SHA256)
- **Permissions** - użytkownik widzi tylko swoje grupy

### 7.2 Sekrety

Przechowywane w zmiennych środowiskowych (`.env`):
- `ALLEGRO_CLIENT_ID`, `ALLEGRO_CLIENT_SECRET`
- `GMAIL_USER`, `GMAIL_APP_PASSWORD`
- `JWT_SECRET_KEY`
- `DATABASE_URL`, `TIMESCALEDB_URL`

### 7.3 Komunikacja zewnętrzna

- HTTPS dla wszystkich endpointów
- TLS dla Gmail SMTP
- OAuth2 dla Allegro
