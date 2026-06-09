import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import type {
  ComparisonResponse,
  GrupaDetail,
  PricesResponse,
} from '../api/types'

export function GroupDetailPage() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const [group, setGroup] = useState<GrupaDetail | null>(null)
  const [prices, setPrices] = useState<PricesResponse | null>(null)
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null)
  const [newProductUrl, setNewProductUrl] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [days, setDays] = useState(30)

  const load = async () => {
    if (!id) return
    const [detail, p, c] = await Promise.all([
      api.get<GrupaDetail>(`/groups/${id}/`),
      api.get<PricesResponse>(`/groups/${id}/prices/`, { params: { days } }),
      api.get<ComparisonResponse>(`/groups/${id}/comparison/`),
    ])
    setGroup(detail.data)
    setPrices(p.data)
    setComparison(c.data)
  }

  useEffect(() => {
    void load()
  }, [id, days])

  const onAddProduct = async (e: FormEvent) => {
    e.preventDefault()
    if (!newProductUrl.trim()) return
    setSubmitting(true)
    setAddError(null)
    try {
      await api.post(`/groups/${id}/products/`, { url: newProductUrl })
      setNewProductUrl('')
      await load()
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Nie udało się dodać produktu.'
      setAddError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const onRefresh = async () => {
    setRefreshing(true)
    try {
      await api.post(`/groups/${id}/refresh/`)
    } finally {
      setRefreshing(false)
    }
  }

  const onDeleteGroup = async () => {
    if (!confirm('Usunąć grupę i wszystkie produkty?')) return
    await api.delete(`/groups/${id}/`)
    nav('/dashboard')
  }

  const onRemoveProduct = async (productId: number) => {
    if (!confirm('Usunąć produkt z grupy? Historia cen zostaje zachowana.')) return
    await api.delete(`/groups/${id}/products/${productId}/`)
    await load()
  }

  if (!group) {
    return <p className="text-slate-500">Ładowanie…</p>
  }

  // Build chart data from PricesResponse: pivot by platform per timestamp
  const chartData = (prices?.dane ?? [])
    .slice()
    .reverse()
    .map((p) => ({
      czas: new Date(p.czas).toLocaleString('pl-PL', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }),
      [p.platforma]: Number(p.najnizsza_cena),
    }))

  const platforms = Array.from(
    new Set((prices?.dane ?? []).map((p) => p.platforma)),
  )
  const PLATFORM_COLORS: Record<string, string> = {
    allegro: '#f97316',
    amazon: '#0ea5e9',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline">
            ← Wróć do grup
          </Link>
          <h1 className="text-2xl font-semibold text-slate-900 mt-1">
            {group.nazwa}
          </h1>
          {group.opis && <p className="text-slate-600 text-sm">{group.opis}</p>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="rounded bg-indigo-600 text-white px-3 py-2 text-sm hover:bg-indigo-700 disabled:opacity-60"
          >
            {refreshing ? 'Odświeżanie…' : 'Odśwież ceny'}
          </button>
          <button
            onClick={onDeleteGroup}
            className="rounded bg-red-100 text-red-700 px-3 py-2 text-sm hover:bg-red-200"
          >
            Usuń grupę
          </button>
        </div>
      </div>

      {comparison && (
        <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-3">Porównanie platform</h2>
          {comparison.najnizsza_cena_globalna ? (
            <p className="text-slate-700 mb-3">
              Najlepsza cena globalna:{' '}
              <strong>{comparison.najnizsza_cena_globalna} PLN</strong> na{' '}
              <strong>{comparison.najlepsza_platforma || 'brak'}</strong>
            </p>
          ) : (
            <p className="text-slate-500 mb-3">Brak danych — dodaj produkty.</p>
          )}
          <table className="w-full text-sm">
            <thead className="text-left text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-2">Platforma</th>
                <th>Najniższa cena</th>
                <th>Sprzedawca</th>
                <th>Liczba sprzedawców</th>
              </tr>
            </thead>
            <tbody>
              {comparison.platformy.map((p) => (
                <tr
                  key={p.produkt_id}
                  className={p.jest_najlepsza ? 'bg-emerald-50' : ''}
                >
                  <td className="py-2 capitalize">{p.platforma}</td>
                  <td>{p.najnizsza_cena ? `${p.najnizsza_cena} PLN` : '—'}</td>
                  <td>{p.najlepszy_sprzedawca || '—'}</td>
                  <td>{p.liczba_sprzedawcow}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Historia cen</h2>
          <label className="text-sm text-slate-600">
            Okres:{' '}
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            >
              <option value={7}>7 dni</option>
              <option value={30}>30 dni</option>
              <option value={90}>90 dni</option>
            </select>
          </label>
        </div>
        {chartData.length === 0 ? (
          <p className="text-slate-500">Brak danych historycznych.</p>
        ) : (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#e2e8f0" />
                <XAxis dataKey="czas" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                {platforms.map((p) => (
                  <Line
                    key={p}
                    type="monotone"
                    dataKey={p}
                    stroke={PLATFORM_COLORS[p] || '#6366f1'}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-3">Dodaj produkt</h2>
        <form onSubmit={onAddProduct} className="flex flex-col gap-2">
          <input
            placeholder="Wklej URL produktu z Allegro lub Amazon"
            value={newProductUrl}
            onChange={(e) => setNewProductUrl(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2"
          />
          {addError && <p className="text-sm text-red-600">{addError}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-indigo-600 text-white py-2 font-medium hover:bg-indigo-700 disabled:opacity-60"
          >
            {submitting ? 'Dodawanie…' : 'Dodaj produkt'}
          </button>
        </form>
      </section>

      <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-3">
          Produkty ({group.produkty.length})
        </h2>
        {group.produkty.length === 0 ? (
          <p className="text-slate-500">Brak produktów w tej grupie.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {group.produkty.map((p) => (
              <li
                key={p.id}
                className="py-3 flex items-center justify-between gap-4"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="inline-block uppercase text-xs font-semibold tracking-wide bg-slate-100 px-2 py-0.5 rounded">
                      {p.platforma}
                    </span>
                    <span className="font-medium text-slate-900 truncate">
                      {p.nazwa || 'Bez nazwy'}
                    </span>
                  </div>
                  <div className="text-sm text-slate-600 mt-1">
                    {p.aktualna_najnizsza_cena
                      ? `${p.aktualna_najnizsza_cena} PLN — ${p.aktualny_najlepszy_sprzedawca || '—'} (${p.liczba_sprzedawcow} oferty)`
                      : 'Brak danych — czekam na fetch'}
                  </div>
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-indigo-600 hover:underline truncate block"
                  >
                    {p.url}
                  </a>
                </div>
                <button
                  onClick={() => onRemoveProduct(p.id)}
                  className="rounded bg-slate-100 text-slate-700 px-3 py-1 text-sm hover:bg-red-100 hover:text-red-700"
                >
                  Usuń
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
