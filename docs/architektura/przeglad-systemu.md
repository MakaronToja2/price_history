# Przegląd Systemu

## 1. Wprowadzenie

**Price History** to inteligentna aplikacja do monitorowania cen produktów w sklepach internetowych z porównywaniem cen między platformami. Użytkownik tworzy grupę produktów (np. "RTX 4080") i dodaje do niej linki z różnych platform (Allegro, Amazon). System śledzi ceny u WSZYSTKICH sprzedawców na każdej platformie, automatycznie wskazuje najlepszą ofertę i powiadamia o okazjach.

### 1.1 Problem biznesowy

- **Ręczne sprawdzanie cen** - czasochłonne i nieefektywne
- **Wielu sprzedawców na jednej platformie** - ten sam produkt oferowany przez dziesiątki sprzedawców w różnych cenach
- **Różnice między platformami** - produkt na Allegro może być droższy niż na Amazon (lub odwrotnie)
- **Przegapione okazje** - błyskawiczne promocje (flash sales) trwają często tylko kilka godzin
- **Brak historii cen** - trudność w ocenie, czy aktualna cena jest rzeczywiście korzystna

### 1.2 Proponowane rozwiązanie

- **Grupy produktów** - jedna grupa = jeden produkt śledzony na wielu platformach
- **Multi-seller monitoring** - automatyczne pobieranie cen wszystkich sprzedawców
- **Cross-platform comparison** - widok porównawczy z jasnym oznaczeniem źródła
- **Smart polling** - dynamiczna częstotliwość sprawdzania
- **Detekcja anomalii** - automatyczne wykrywanie flash sales

---

## 2. Cele projektu

### 2.1 Cele funkcjonalne

| ID | Cel | Priorytet |
|----|-----|-----------|
| F1 | Grupy produktów (cross-platform comparison) | Wysoki |
| F2 | Śledzenie cen z Allegro (API) - wszyscy sprzedawcy | Wysoki |
| F3 | Śledzenie cen z Amazon (scraper) - wszyscy sprzedawcy | Wysoki |
| F4 | Historia najniższych cen z analizą | Wysoki |
| F5 | Automatyczne wykrywanie flash sales | Wysoki |
| F6 | Smart polling - dynamiczna częstotliwość | Wysoki |
| F7 | Powiadomienia email | Średni |
| F8 | Wizualizacja na wykresach (per platforma) | Średni |

### 2.2 Cele niefunkcjonalne

| ID | Cel | Kryterium sukcesu |
|----|-----|-------------------|
| NF1 | Skalowalność | Obsługa 10,000+ rekordów cen dziennie |
| NF2 | Niezawodność | Automatyczne ponawianie nieudanych zapytań |
| NF3 | Wydajność | Czas odpowiedzi API < 200ms |
| NF4 | Bezpieczeństwo | Uwierzytelnianie JWT, szyfrowane hasła |
| NF5 | Rozszerzalność | Łatwe dodawanie nowych platform (architektura plugin-like) |

---

## 3. Zakres systemu

### 3.1 W zakresie projektu (v1)

- Backend REST API (Django + DRF)
- Frontend SPA (React + TypeScript)
- Grupy produktów z porównaniem cross-platform
- Integracja z Allegro API (OAuth2) - wszystkie oferty produktu
- Web scraper dla Amazon (Playwright) - wszyscy sprzedawcy
- System zadań w tle (Celery + Redis, multi-queue)
- PostgreSQL (dane transakcyjne) + TimescaleDB (szeregi czasowe)
- Powiadomienia email (Gmail SMTP)
- Smart polling (volatility-based scheduling)
- Detekcja anomalii (Z-score)

### 3.2 Poza zakresem projektu (v1)

- Aplikacja mobilna
- Automatyczne sugerowanie podobnych produktów (fuzzy matching)
- Dodatkowe platformy (Ceneo, MediaExpert, RTV Euro AGD, x-kom)
- Predykcja cen (ML)
- CI/CD pipeline
- Wdrożenie produkcyjne

### 3.3 Planowane rozszerzenia (v2)

- **Auto-rekomendacje** - sugerowanie podobnych ofert
- **Dodatkowe platformy** - Ceneo, MediaExpert, RTV Euro AGD, x-kom, Morele.net
- **Predykcja cenowa** - model ML przewidujący trendy

---

## 4. Użytkownicy docelowi

### 4.1 Persony użytkowników

**Łowca okazji (primary)**
- Aktywnie szuka promocji
- Śledzi elektronikę (zmienne ceny)
- Chce natychmiastowych alertów o flash sales
- Korzysta z wielu platform - potrzebuje porównania

**Planujący zakup**
- Planuje większy zakup (np. laptop)
- Chce poczekać na najlepszą cenę
- Interesuje go historia i trendy
- Ustawia próg cenowy i czeka na alert

---

## 5. Kluczowe funkcjonalności

### 5.1 Grupy Produktów (Cross-Platform Comparison)

Najważniejsza funkcjonalność systemu. Użytkownik:

1. **Tworzy grupę** - np. "RTX 4080"
2. **Dodaje linki z różnych platform** - jeden z Allegro, jeden z Amazon
3. **System tracking each platform independently**:
   - Pobiera ceny od wszystkich sprzedawców na każdej platformie
   - Wybiera najniższą cenę per platforma
4. **Wyświetla porównanie**:
   ```
   RTX 4080 - Najniższa cena globalna: 2399 PLN
   ├── Amazon:  2399 PLN (Sprzedawca: TechStore)  ← NAJLEPSZA
   └── Allegro: 2499 PLN (Sprzedawca: SuperSklep)
   ```
5. **Alerty triggerują na najniższej cenie w całej grupie**

### 5.2 Multi-Seller Monitoring (per platforma)

Dla każdego produktu w grupie system pobiera ceny WSZYSTKICH sprzedawców:

| Platforma | Identifier | Co pobieramy |
|-----------|------------|--------------|
| Allegro | Product ID z URL | API zwraca wszystkie oferty produktu |
| Amazon | ASIN z URL | Scraper wyciąga Buy Box + "Other Sellers" |

System zapisuje wszystkie ceny w historii, flagując najniższą.

### 5.3 Smart Polling (Inteligentne harmonogramowanie)

```
Współczynnik zmienności (CV) = odchylenie_std / średnia

Mapowanie na interwały:
- CV < 0.2  → co 24h (produkty stabilne)
- CV 0.2-0.4 → co 6h
- CV 0.4-0.6 → co 2h
- CV 0.6-0.8 → co 1h
- CV > 0.8  → co 15 min (produkty zmienne)
```

**Korzyści:**
- Oszczędność zasobów dla stabilnych produktów
- Szybsze wykrywanie okazji dla zmiennych produktów
- Zmniejszone ryzyko blokady przez anty-bot systemy

### 5.4 Detekcja anomalii (Flash Sale Detector)

```
Z-score = (aktualna_cena - średnia_14d) / odchylenie_std_14d

Jeśli Z-score < -2 (cena > 2σ poniżej średniej):
→ Wykryto FLASH SALE
→ Automatyczny alert (bez progu użytkownika)
```

### 5.5 Architektura dwóch baz danych

| Baza | Typ danych | Uzasadnienie |
|------|------------|--------------|
| PostgreSQL | Użytkownicy, grupy, produkty, sprzedawcy, alerty | Dane transakcyjne, relacje |
| TimescaleDB | Historia cen (wszyscy sprzedawcy) | Zoptymalizowane zapytania czasowe, retencja |

---

## 6. Stos technologiczny

### 6.1 Backend

| Komponent | Technologia | Uzasadnienie |
|-----------|-------------|--------------|
| Framework | Django 5.x | Dojrzały, bogaty ekosystem, ORM |
| REST API | Django REST Framework | Standard dla API w Django |
| Uwierzytelnianie | djangorestframework-simplejwt | JWT tokens, bezstanowe |
| Zadania w tle | Celery 5.x | Niezawodne, skalowalne |
| Broker | Redis | Szybki, prosty w konfiguracji |
| Analityka | Pandas, NumPy | Standard do analizy danych |

### 6.2 Bazy danych

| Baza | Wersja | Zastosowanie |
|------|--------|--------------|
| PostgreSQL | 15 | Dane transakcyjne |
| TimescaleDB | latest-pg15 | Szeregi czasowe (hypertabele) |

### 6.3 Frontend

| Komponent | Technologia | Uzasadnienie |
|-----------|-------------|--------------|
| Framework | React 18 | Popularny, komponentowy |
| Język | TypeScript | Typowanie statyczne |
| Stylowanie | TailwindCSS | Utility-first |
| Wykresy | Recharts | Dobre wsparcie React |
| HTTP Client | Axios | Interceptory, obsługa błędów |

### 6.4 Pozyskiwanie danych

| Źródło | Metoda | Co pobieramy |
|--------|--------|--------------|
| Allegro | REST API (OAuth2) | Wszystkie oferty produktu, ceny, sprzedawcy |
| Amazon | Web scraping (Playwright) | Buy Box + "Other Sellers" |

---

## 7. Wysokopoziomowa architektura

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                    │
│                     React + TypeScript                               │
│      (Grupy produktów, Porównanie platform, Wykresy, Alerty)         │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST API (JWT)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          BACKEND                                     │
│                     Django + DRF                                     │
│                                                                      │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐  │
│   │  Users   │  │  Groups  │  │ Products │  │ Sellers  │  │Alerts│  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────┘  │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Silnik Statystyk (Pandas)                       │   │
│   │    - Wskaźnik zmienności   - Detekcja anomalii (Z-score)     │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────┬─────────────────────────────────────────────┬─────────────┘
          │                                             │
          ▼                                             ▼
┌───────────────────┐                     ┌───────────────────────────┐
│    PostgreSQL     │                     │        TimescaleDB        │
│  (Transakcyjne)   │                     │     (Szeregi czasowe)     │
│                   │                     │                           │
│  - użytkownicy    │                     │  - historia_cen           │
│  - grupy          │                     │    (wszyscy sprzedawcy)   │
│  - produkty       │                     │  - flag jest_najnizsza    │
│  - sprzedawcy     │                     │  - agregaty dzienne       │
│  - alerty         │                     │                           │
└───────────────────┘                     └───────────────────────────┘

┌───────────────────┐         ┌───────────────────────────────────────┐
│      Redis        │◄────────│           Workery Celery              │
│ (Broker wiadom.)  │         │  - Allegro Client (wszystkie oferty)  │
└───────────────────┘         │  - Amazon Scraper (wszyscy sprzedawcy)│
                              │  - Email Sender     - Analytics       │
                              └───────────────────────────────────────┘
```

---

## 8. Kluczowe decyzje architektoniczne

| Decyzja | Wybór | Alternatywy | Uzasadnienie |
|---------|-------|-------------|--------------|
| Framework backend | Django + DRF | FastAPI, Flask | Dojrzałość, ORM, admin panel |
| Baza szeregów czasowych | TimescaleDB | InfluxDB, vanilla PostgreSQL | Kompatybilność z PostgreSQL, SQL |
| Obliczenia analityczne | Pandas (on-demand) | Tylko DB aggregates | Elastyczność dla złożonych obliczeń |
| Web scraping | Playwright | Selenium, BeautifulSoup | Obsługa JavaScript |
| Model śledzenia | Grupy + produkty per platforma | Pojedyncze URLs | Cross-platform comparison |

Szczegóły: `docs/decyzje/`

---

## 9. Ograniczenia i ryzyka

### 9.1 Ograniczenia techniczne

- **Rate limiting Allegro API** - kolejkowanie zapytań
- **Anti-bot Amazon** - rotacja user-agentów, smart polling
- **Manualne grupowanie** - użytkownik sam dodaje linki (auto-matching to v2)

### 9.2 Ryzyka projektu

| Ryzyko | Prawdopod. | Wpływ | Mitygacja |
|--------|------------|-------|-----------|
| Zmiana DOM Amazon | Wysoka | Średni | Regularne testy, alerty błędów |
| Zmiana API Allegro | Niska | Wysoki | Śledzenie dokumentacji |
| Blokada przez Amazon | Średnia | Wysoki | Smart polling, rotacja user-agent |

---

## 10. Słownik pojęć

| Termin | Definicja |
|--------|-----------|
| **Grupa produktów** | Logiczna grupa stworzona przez użytkownika łącząca ten sam produkt z różnych platform |
| **ASIN** | Amazon Standard Identification Number - identyfikator produktu Amazon |
| **Product ID** | Identyfikator produktu na Allegro |
| **Volatility Score** | Wskaźnik zmienności ceny (0.0-1.0) |
| **Smart Polling** | Dynamiczna częstotliwość sprawdzania |
| **Flash Sale** | Błyskawiczna promocja (auto-detected) |
| **Z-score** | Miara odległości od średniej w jednostkach σ |
| **Hypertabela** | Tabela TimescaleDB dla szeregów czasowych |
| **Multi-Seller Monitoring** | Śledzenie wszystkich sprzedawców produktu |
| **Cross-Platform Comparison** | Porównanie najniższych cen między platformami |
