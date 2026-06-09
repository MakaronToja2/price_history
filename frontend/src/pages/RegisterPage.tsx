import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function RegisterPage() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError('Hasła nie są identyczne.')
      return
    }
    setLoading(true)
    try {
      await register(email, password, confirm)
      nav('/dashboard', { replace: true })
    } catch {
      setError('Rejestracja nie powiodła się. Sprawdź wymagania hasła.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white border border-slate-200 rounded-lg shadow-sm p-6 space-y-4"
      >
        <h1 className="text-2xl font-semibold text-slate-900">Rejestracja</h1>
        <label className="block">
          <span className="text-sm text-slate-700">Email</span>
          <input
            type="email"
            value={email}
            required
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:outline-none focus:ring focus:ring-indigo-200"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Hasło (min. 8 znaków)</span>
          <input
            type="password"
            value={password}
            required
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:outline-none focus:ring focus:ring-indigo-200"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Powtórz hasło</span>
          <input
            type="password"
            value={confirm}
            required
            onChange={(e) => setConfirm(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:outline-none focus:ring focus:ring-indigo-200"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-indigo-600 text-white py-2 font-medium hover:bg-indigo-700 disabled:opacity-60"
        >
          {loading ? 'Rejestracja…' : 'Załóż konto'}
        </button>
        <p className="text-sm text-slate-600 text-center">
          Masz już konto?{' '}
          <Link to="/login" className="text-indigo-600 hover:underline">
            Zaloguj się
          </Link>
        </p>
      </form>
    </div>
  )
}
