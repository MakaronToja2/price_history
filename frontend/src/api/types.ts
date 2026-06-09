export interface Tokens {
  access: string
  refresh: string
}

export interface CurrentUser {
  id: number
  email: string
  utworzono: string
  liczba_grup: number
  liczba_aktywnych_alertow: number
}

export interface GrupaListItem {
  id: number
  nazwa: string
  opis: string
  url_obrazka: string | null
  najnizsza_cena_globalna: string | null
  najlepsza_platforma: string
  najlepszy_sprzedawca: string
  cena_docelowa: string | null
  aktywny: boolean
  liczba_produktow: number
  utworzono: string
}

export interface ProduktSummary {
  id: number
  platforma: string
  nazwa: string
  url: string
  aktualna_najnizsza_cena: string | null
  aktualny_najlepszy_sprzedawca: string | null
  wskaznik_zmiennosci: string | null
  liczba_sprzedawcow: number
  ostatnie_sprawdzenie: string | null
}

export interface GrupaDetail extends GrupaListItem {
  produkty: ProduktSummary[]
}

export interface PricePoint {
  czas: string
  najnizsza_cena: string
  platforma: string
  sprzedawca: string
}

export interface PricesResponse {
  grupa_id: number
  dane: PricePoint[]
}

export interface PlatformComparison {
  platforma: string
  produkt_id: number
  najnizsza_cena: string | null
  najlepszy_sprzedawca: string
  liczba_sprzedawcow: number
  jest_najlepsza: boolean
}

export interface ComparisonResponse {
  grupa_id: number
  nazwa: string
  najnizsza_cena_globalna: string | null
  najlepsza_platforma: string
  platformy: PlatformComparison[]
}

export type AlertType = 'docelowy' | 'spadek_ceny' | 'flash_sale'

export interface Alert {
  id: number
  grupa_id: number
  grupa_nazwa: string
  typ_alertu: AlertType
  prog_ceny: string | null
  prog_procent: string | null
  aktywny: boolean
  ostatnie_wyzwolenie: string | null
  utworzono: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
