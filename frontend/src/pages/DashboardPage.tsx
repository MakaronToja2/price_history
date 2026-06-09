import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { GrupaListItem, Paginated } from '../api/types'

export function DashboardPage() {
  const [groups, setGroups] = useState<GrupaListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newOpis, setNewOpis] = useState('')
  const [newTarget, setNewTarget] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [search, setSearch] = useState('')

  const load = async (q?: string) => {
    setLoading(true)
    try {
      const res = await api.get<Paginated<GrupaListItem>>('/groups/', {
        params: q ? { search: q } : undefined,
      })
      setGroups(res.data.results)
    } catch {
      setError('Nie udało się pobrać grup.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      await api.post('/groups/', {
        nazwa: newName,
        opis: newOpis,
        cena_docelowa: newTarget || null,
      })
      setNewName('')
      setNewOpis('')
      setNewTarget('')
      await load(search)
    } catch {
      setError('Nie udało się utworzyć grupy.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Nowa grupa</h2>
        <form onSubmit={onCreate} className="grid gap-3 md:grid-cols-4">
          <input
            placeholder="Nazwa (np. RTX 4080)"
            required
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="md:col-span-2 rounded border border-slate-300 px-3 py-2"
          />
          <input
            placeholder="Opis (opcjonalny)"
            value={newOpis}
            onChange={(e) => setNewOpis(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2"
          />
          <input
            placeholder="Cena docelowa"
            type="number"
            step="0.01"
            value={newTarget}
            onChange={(e) => setNewTarget(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2"
          />
          <button
            type="submit"
            disabled={submitting}
            className="md:col-span-4 rounded bg-indigo-600 text-white py-2 font-medium hover:bg-indigo-700 disabled:opacity-60"
          >
            {submitting ? 'Zapisywanie…' : 'Dodaj grupę'}
          </button>
        </form>
      </section>

      <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between gap-4 mb-4">
          <h2 className="text-lg font-semibold">Twoje grupy</h2>
          <input
            placeholder="Szukaj…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              void load(e.target.value)
            }}
            className="rounded border border-slate-300 px-3 py-1 text-sm"
          />
        </div>

        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
        {loading ? (
          <p className="text-slate-500">Ładowanie…</p>
        ) : groups.length === 0 ? (
          <p className="text-slate-500">Brak grup. Utwórz pierwszą powyżej.</p>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {groups.map((g) => (
              <li key={g.id}>
                <Link
                  to={`/groups/${g.id}`}
                  className="block border border-slate-200 rounded-md p-4 hover:border-indigo-400 hover:shadow-sm transition"
                >
                  <div className="flex items-baseline justify-between">
                    <h3 className="font-semibold text-slate-900">{g.nazwa}</h3>
                    <span className="text-sm text-slate-500">
                      {g.liczba_produktow} produkt.
                    </span>
                  </div>
                  {g.opis && (
                    <p className="text-sm text-slate-600 mt-1">{g.opis}</p>
                  )}
                  <div className="mt-2 text-sm text-slate-700">
                    {g.najnizsza_cena_globalna ? (
                      <>
                        Najlepiej: <strong>{g.najnizsza_cena_globalna} PLN</strong>{' '}
                        ({g.najlepsza_platforma || 'brak'})
                      </>
                    ) : (
                      <span className="text-slate-500">Brak danych cenowych</span>
                    )}
                  </div>
                  {g.cena_docelowa && (
                    <div className="text-xs text-slate-500 mt-1">
                      Cena docelowa: {g.cena_docelowa} PLN
                    </div>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
