import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/dashboard" className="text-lg font-semibold text-slate-900">
            Price History Scanner
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/dashboard" className="hover:text-indigo-600">
              Grupy
            </Link>
            <Link to="/alerts" className="hover:text-indigo-600">
              Alerty
            </Link>
            {user && (
              <>
                <span className="text-slate-500">{user.email}</span>
                <button
                  type="button"
                  onClick={() => {
                    logout()
                    nav('/login')
                  }}
                  className="rounded bg-slate-100 px-3 py-1 hover:bg-slate-200"
                >
                  Wyloguj
                </button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
