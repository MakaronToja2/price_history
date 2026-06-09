import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Alert, AlertType, GrupaListItem, Paginated } from '../api/types'

const TYP_LABELS: Record<AlertType, string> = {
  docelowy: 'Cena docelowa',
  spadek_ceny: 'Spadek o %',
  flash_sale: 'Flash sale (auto)',
}

export function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [groups, setGroups] = useState<GrupaListItem[]>([])
  const [groupId, setGroupId] = useState<number | ''>('')
  const [typ, setTyp] = useState<AlertType>('docelowy')
  const [progCeny, setProgCeny] = useState('')
  const [progProc, setProgProc] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    const [a, g] = await Promise.all([
      api.get<Paginated<Alert>>('/alerts/'),
      api.get<Paginated<GrupaListItem>>('/groups/'),
    ])
    setAlerts(a.data.results)
    setGroups(g.data.results)
    if (g.data.results.length > 0 && groupId === '') {
      setGroupId(g.data.results[0].id)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!groupId) {
      setError('Wybierz grupę.')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const payload: Record<string, unknown> = { typ_alertu: typ }
      if (typ === 'docelowy') payload.prog_ceny = progCeny
      if (typ === 'spadek_ceny') payload.prog_procent = progProc
      await api.post(`/groups/${groupId}/alerts/`, payload)
      setProgCeny('')
      setProgProc('')
      await load()
    } catch (err) {
      const detail =
        (err as { response?: { data?: Record<string, string[] | string> } })?.response
          ?.data ?? {}
      setError(JSON.stringify(detail))
    } finally {
      setSubmitting(false)
    }
  }

  const onDelete = async (id: number) => {
    if (!confirm('Usunąć ten alert?')) return
    await api.delete(`/alerts/${id}/`)
    await load()
  }

  return (
    <div className="space-y-6">
      <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Nowy alert</h2>
        {groups.length === 0 ? (
          <p className="text-slate-500">
            Najpierw utwórz grupę produktów w zakładce „Grupy”.
          </p>
        ) : (
          <form onSubmit={onCreate} className="grid gap-3 md:grid-cols-4">
            <select
              value={groupId}
              onChange={(e) => setGroupId(Number(e.target.value))}
              className="rounded border border-slate-300 px-3 py-2"
            >
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nazwa}
                </option>
              ))}
            </select>
            <select
              value={typ}
              onChange={(e) => setTyp(e.target.value as AlertType)}
              className="rounded border border-slate-300 px-3 py-2"
            >
              {(Object.keys(TYP_LABELS) as AlertType[]).map((t) => (
                <option key={t} value={t}>
                  {TYP_LABELS[t]}
                </option>
              ))}
            </select>
            {typ === 'docelowy' && (
              <input
                placeholder="Cena docelowa (PLN)"
                type="number"
                step="0.01"
                required
                value={progCeny}
                onChange={(e) => setProgCeny(e.target.value)}
                className="rounded border border-slate-300 px-3 py-2"
              />
            )}
            {typ === 'spadek_ceny' && (
              <input
                placeholder="Próg spadku (%)"
                type="number"
                step="0.1"
                required
                value={progProc}
                onChange={(e) => setProgProc(e.target.value)}
                className="rounded border border-slate-300 px-3 py-2"
              />
            )}
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-indigo-600 text-white px-3 py-2 font-medium hover:bg-indigo-700 disabled:opacity-60"
            >
              {submitting ? 'Zapisywanie…' : 'Dodaj alert'}
            </button>
            {error && (
              <p className="md:col-span-4 text-sm text-red-600 whitespace-pre-wrap">
                {error}
              </p>
            )}
          </form>
        )}
      </section>

      <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">
          Twoje alerty ({alerts.length})
        </h2>
        {alerts.length === 0 ? (
          <p className="text-slate-500">Brak alertów.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {alerts.map((a) => (
              <li
                key={a.id}
                className="py-3 flex items-center justify-between gap-4"
              >
                <div>
                  <div className="font-medium text-slate-900">{a.grupa_nazwa}</div>
                  <div className="text-sm text-slate-600">
                    {TYP_LABELS[a.typ_alertu]}{' '}
                    {a.prog_ceny && ` — przy cenie ${a.prog_ceny} PLN`}
                    {a.prog_procent && ` — spadek o ${a.prog_procent}%`}
                  </div>
                  {a.ostatnie_wyzwolenie && (
                    <div className="text-xs text-slate-500 mt-1">
                      Ostatnie wyzwolenie:{' '}
                      {new Date(a.ostatnie_wyzwolenie).toLocaleString('pl-PL')}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => onDelete(a.id)}
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
