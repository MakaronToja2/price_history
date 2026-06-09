import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-slate-500">
        Ładowanie…
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return <>{children}</>
}
