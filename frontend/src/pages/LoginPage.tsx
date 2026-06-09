import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const nav = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname
      nav(from || '/dashboard', { replace: true })
    } catch {
      setError('Nieprawidłowy email lub hasło.')
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
        <h1 className="text-2xl font-semibold text-slate-900">Logowanie</h1>
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
          <span className="text-sm text-slate-700">Hasło</span>
          <input
            type="password"
            value={password}
            required
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:outline-none focus:ring focus:ring-indigo-200"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-indigo-600 text-white py-2 font-medium hover:bg-indigo-700 disabled:opacity-60"
        >
          {loading ? 'Logowanie…' : 'Zaloguj się'}
        </button>
        <p className="text-sm text-slate-600 text-center">
          Nie masz konta?{' '}
          <Link to="/register" className="text-indigo-600 hover:underline">
            Zarejestruj się
          </Link>
        </p>
      </form>
    </div>
  )
}
