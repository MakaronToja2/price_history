# Endpointy REST API

## 1. Wprowadzenie

System Price History udostępnia REST API zgodne z konwencjami Django REST Framework. Wszystkie endpointy (poza autoryzacją) wymagają tokena JWT.

**Base URL:** `http://localhost:8000/api/`
**Format danych:** JSON
**Autoryzacja:** `Authorization: Bearer <jwt_token>`

---

## 2. Konwencje

### 2.1 Format odpowiedzi

**Sukces:**
```json
{
    "id": 42,
    "field": "value"
}
```

**Lista (z paginacją):**
```json
{
    "count": 100,
    "next": "http://localhost:8000/api/groups/?page=2",
    "previous": null,
    "results": [...]
}
```

**Błąd:**
```json
{
    "detail": "Authentication credentials were not provided.",
    "code": "not_authenticated"
}
```

### 2.2 Kody statusu HTTP

| Kod | Znaczenie |
|-----|-----------|
| 200 | OK - operacja udana |
| 201 | Created - zasób utworzony |
| 204 | No Content - operacja udana, brak treści |
| 400 | Bad Request - błędne dane |
| 401 | Unauthorized - brak/zły token JWT |
| 403 | Forbidden - brak uprawnień |
| 404 | Not Found - zasób nie istnieje |
| 429 | Too Many Requests - rate limit |
| 500 | Internal Server Error |

### 2.3 Paginacja

Domyślnie 20 rekordów na stronę. Parametry:
- `?page=2` - numer strony
- `?page_size=50` - rozmiar strony (max 100)

---

## 3. Autoryzacja

### 3.1 Rejestracja

**`POST /api/auth/register/`**

Tworzy nowe konto użytkownika.

**Request:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
}
```

**Response (201):**
```json
{
    "id": 1,
    "email": "user@example.com",
    "access": "eyJ0eXAiOi...",
    "refresh": "eyJ0eXAiOi..."
}
```

**Walidacje:**
- Email musi być unikalny
- Hasło: min 8 znaków, mix wielkich/małych liter, cyfra
- `password` === `password_confirm`

---

### 3.2 Logowanie

**`POST /api/auth/login/`**

Pobiera tokeny JWT.

**Request:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
    "access": "eyJ0eXAiOi...",
    "refresh": "eyJ0eXAiOi..."
}
```

**Lifespan tokenów:**
- `access`: 15 minut
- `refresh`: 7 dni

---

### 3.3 Odświeżanie tokena

**`POST /api/auth/refresh/`**

Wymienia refresh token na nowy access token.

**Request:**
```json
{
    "refresh": "eyJ0eXAiOi..."
}
```

**Response (200):**
```json
{
    "access": "eyJ0eXAiOi..."
}
```

---

### 3.4 Aktualny użytkownik

**`GET /api/auth/me/`**

Zwraca dane zalogowanego użytkownika.

**Response (200):**
```json
{
    "id": 1,
    "email": "user@example.com",
    "utworzono": "2026-04-25T10:00:00Z",
    "liczba_grup": 5,
    "liczba_aktywnych_alertow": 3
}
```

---

## 4. Grupy produktów

### 4.1 Lista grup użytkownika

**`GET /api/groups/`**

Zwraca grupy produktów zalogowanego użytkownika.

**Query params:**
- `?aktywny=true` - tylko aktywne
- `?search=rtx` - wyszukiwanie po nazwie

**Response (200):**
```json
{
    "count": 3,
    "results": [
        {
            "id": 1,
            "nazwa": "RTX 4080",
            "opis": "Karta graficzna do PC",
            "url_obrazka": "https://...",
            "najnizsza_cena_globalna": 2399.00,
            "najlepsza_platforma": "amazon",
            "najlepszy_sprzedawca": "TechStore",
            "cena_docelowa": 2200.00,
            "aktywny": true,
            "liczba_produktow": 2,
            "utworzono": "2026-04-20T10:00:00Z"
        }
    ]
}
```

---

### 4.2 Utworzenie grupy

**`POST /api/groups/`**

Tworzy nową grupę produktów.

**Request:**
```json
{
    "nazwa": "RTX 4080",
    "opis": "Karta graficzna do PC",
    "cena_docelowa": 2200.00
}
```

**Response (201):**
```json
{
    "id": 1,
    "nazwa": "RTX 4080",
    "opis": "Karta graficzna do PC",
    "url_obrazka": null,
    "najnizsza_cena_globalna": null,
    "cena_docelowa": 2200.00,
    "aktywny": true,
    "utworzono": "2026-04-25T10:00:00Z"
}
```

---

### 4.3 Szczegóły grupy

**`GET /api/groups/{id}/`**

Zwraca szczegóły grupy z produktami.

**Response (200):**
```json
{
    "id": 1,
    "nazwa": "RTX 4080",
    "najnizsza_cena_globalna": 2399.00,
    "najlepsza_platforma": "amazon",
    "najlepszy_sprzedawca": "TechStore",
    "cena_docelowa": 2200.00,
    "produkty": [
        {
            "id": 10,
            "platforma": "allegro",
            "nazwa": "Karta graficzna RTX 4080 SUPER",
            "url": "https://allegro.pl/oferta/...",
            "aktualna_najnizsza_cena": 2499.00,
            "aktualny_najlepszy_sprzedawca": "SuperSklep",
            "wskaznik_zmiennosci": 0.65,
            "liczba_sprzedawcow": 5,
            "ostatnie_sprawdzenie": "2026-04-25T09:45:00Z"
        },
        {
            "id": 11,
            "platforma": "amazon",
            "nazwa": "NVIDIA RTX 4080",
            "url": "https://amazon.pl/dp/...",
            "aktualna_najnizsza_cena": 2399.00,
            "aktualny_najlepszy_sprzedawca": "TechStore",
            "wskaznik_zmiennosci": 0.72,
            "liczba_sprzedawcow": 3,
            "ostatnie_sprawdzenie": "2026-04-25T09:50:00Z"
        }
    ]
}
```

---

### 4.4 Aktualizacja grupy

**`PATCH /api/groups/{id}/`**

Częściowa aktualizacja grupy.

**Request:**
```json
{
    "cena_docelowa": 2100.00
}
```

**Response (200):** zaktualizowana grupa.

---

### 4.5 Usunięcie grupy

**`DELETE /api/groups/{id}/`**

Usuwa grupę i wszystkie powiązane produkty (CASCADE).

**Response (204):** No Content.

---

### 4.6 Historia cen grupy

**`GET /api/groups/{id}/prices/`**

Zwraca historię najniższych cen cross-platform.

**Query params:**
- `?days=30` - liczba dni (domyślnie 30)
- `?granularity=hour` - granularność (`hour`, `day`)

**Response (200):**
```json
{
    "grupa_id": 1,
    "dane": [
        {
            "czas": "2026-04-25T10:00:00Z",
            "najnizsza_cena": 2399.00,
            "platforma": "amazon",
            "sprzedawca": "TechStore"
        },
        {
            "czas": "2026-04-25T09:00:00Z",
            "najnizsza_cena": 2449.00,
            "platforma": "allegro",
            "sprzedawca": "SuperSklep"
        }
    ]
}
```

---

### 4.7 Porównanie platform

**`GET /api/groups/{id}/comparison/`**

Snapshot aktualnych cen na każdej platformie.

**Response (200):**
```json
{
    "grupa_id": 1,
    "nazwa": "RTX 4080",
    "najnizsza_cena_globalna": 2399.00,
    "najlepsza_platforma": "amazon",
    "platformy": [
        {
            "platforma": "amazon",
            "produkt_id": 11,
            "najnizsza_cena": 2399.00,
            "najlepszy_sprzedawca": "TechStore",
            "liczba_sprzedawcow": 3,
            "trend_24h": "down",
            "zmiana_procent_24h": -2.5,
            "jest_najlepsza": true
        },
        {
            "platforma": "allegro",
            "produkt_id": 10,
            "najnizsza_cena": 2499.00,
            "najlepszy_sprzedawca": "SuperSklep",
            "liczba_sprzedawcow": 5,
            "trend_24h": "stable",
            "zmiana_procent_24h": 0.0,
            "jest_najlepsza": false
        }
    ]
}
```

---

### 4.8 Wymuszenie odświeżenia

**`POST /api/groups/{id}/refresh/`**

Wymusza natychmiastowe sprawdzenie cen wszystkich produktów w grupie.

**Response (202):**
```json
{
    "message": "Refresh queued",
    "task_ids": ["abc-123", "def-456"]
}
```

---

## 5. Produkty (w ramach grupy)

### 5.1 Dodanie produktu do grupy

**`POST /api/groups/{group_id}/products/`**

Dodaje link do grupy. System automatycznie wykrywa platformę i ekstraktuje identyfikator.

**Request:**
```json
{
    "url": "https://allegro.pl/oferta/rtx-4080-...-12345"
}
```

**Response (201):**
```json
{
    "id": 10,
    "grupa_id": 1,
    "platforma": "allegro",
    "zewnetrzny_id": "12345",
    "nazwa": "Karta graficzna RTX 4080",
    "url": "https://allegro.pl/oferta/...",
    "aktywny": true,
    "ostatnie_sprawdzenie": null,
    "task_id": "abc-123"
}
```

**Błędy:**
- `400`: Nieobsługiwana platforma
- `400`: Nie można wyekstraktować identyfikatora
- `400`: Produkt już istnieje w grupie

---

### 5.2 Lista produktów w grupie

**`GET /api/groups/{group_id}/products/`**

Zwraca produkty w grupie (per platforma).

---

### 5.3 Usunięcie produktu z grupy

**`DELETE /api/groups/{group_id}/products/{product_id}/`**

Usuwa produkt z grupy. Historia cen pozostaje (TimescaleDB) ale produkt staje się nieaktywny.

**Response (204):** No Content.

---

### 5.4 Historia cen produktu (per platforma)

**`GET /api/products/{id}/prices/`**

Historia cen dla konkretnego produktu na konkretnej platformie.

**Query params:**
- `?days=30`
- `?seller_id=7` - filtruj po sprzedawcy
- `?only_lowest=true` - tylko najniższe ceny

**Response (200):**
```json
{
    "produkt_id": 10,
    "dane": [
        {
            "czas": "2026-04-25T10:00:00Z",
            "sprzedawca": {
                "id": 7,
                "nazwa": "TechStore"
            },
            "cena": 2399.00,
            "jest_najnizsza": true
        }
    ]
}
```

---

### 5.5 Lista sprzedawców produktu

**`GET /api/products/{id}/sellers/`**

Aktualni sprzedawcy oferujący produkt.

**Response (200):**
```json
{
    "produkt_id": 10,
    "sprzedawcy": [
        {
            "id": 7,
            "nazwa": "TechStore",
            "ocena": 4.85,
            "aktualna_cena": 2399.00,
            "url_profilu": "https://...",
            "jest_najlepszy": true
        }
    ]
}
```

---

## 6. Analityka

### 6.1 Statystyki grupy

**`GET /api/groups/{id}/stats/`**

**Response (200):**
```json
{
    "grupa_id": 1,
    "okres_dni": 30,
    "najnizsza_cena_kiedykolwiek": 2299.00,
    "najwyzsza_cena_kiedykolwiek": 2899.00,
    "srednia_cena_30d": 2549.00,
    "odchylenie_std_30d": 124.50,
    "trend_30d": "down",
    "zmiana_procent_30d": -8.5,
    "wykryte_anomalie": 3,
    "platforma_najczesciej_najlepsza": "amazon"
}
```

---

### 6.2 Statystyki produktu

**`GET /api/products/{id}/stats/`**

Statystyki dla produktu na konkretnej platformie.

---

### 6.3 Wykryte anomalie

**`GET /api/groups/{id}/anomalies/`**

Lista wykrytych flash sales w grupie.

**Response (200):**
```json
{
    "grupa_id": 1,
    "anomalie": [
        {
            "czas": "2026-04-23T14:30:00Z",
            "platforma": "amazon",
            "sprzedawca": "TechStore",
            "cena": 2199.00,
            "srednia_okolic": 2549.00,
            "z_score": -2.81,
            "spadek_procent": 13.7,
            "alert_wyslany": true
        }
    ]
}
```

---

## 7. Alerty

### 7.1 Lista alertów

**`GET /api/alerts/`**

Zwraca alerty użytkownika.

**Response (200):**
```json
{
    "results": [
        {
            "id": 1,
            "grupa_id": 1,
            "grupa_nazwa": "RTX 4080",
            "typ_alertu": "docelowy",
            "prog_ceny": 2200.00,
            "aktywny": true,
            "ostatnie_wyzwolenie": null,
            "utworzono": "2026-04-25T10:00:00Z"
        }
    ]
}
```

---

### 7.2 Utworzenie alertu

**`POST /api/groups/{group_id}/alerts/`**

**Request (target price):**
```json
{
    "typ_alertu": "docelowy",
    "prog_ceny": 2200.00
}
```

**Request (price drop %):**
```json
{
    "typ_alertu": "spadek_ceny",
    "prog_procent": 10.0
}
```

**Request (flash sale - auto):**
```json
{
    "typ_alertu": "flash_sale"
}
```

**Response (201):** utworzony alert.

---

### 7.3 Aktualizacja alertu

**`PATCH /api/alerts/{id}/`**

---

### 7.4 Usunięcie alertu

**`DELETE /api/alerts/{id}/`**

---

## 8. Rate limiting

| Endpoint | Limit |
|----------|-------|
| `/api/auth/login/` | 5 prób / 15 min / IP |
| `/api/auth/register/` | 3 / godz. / IP |
| `/api/groups/{id}/refresh/` | 1 / minuta / użytkownik |
| Pozostałe | 1000 / godz. / użytkownik |

---

## 9. Webhooks (przyszłość v2)

Planowane endpointy v2:
- `POST /api/webhooks/` - rejestracja webhook URL
- Powiadomienia push o flash sales

---

## 10. OpenAPI / Swagger

Dokumentacja interaktywna dostępna pod:
- **Swagger UI:** `/api/docs/`
- **ReDoc:** `/api/redoc/`
- **OpenAPI JSON:** `/api/schema/`
