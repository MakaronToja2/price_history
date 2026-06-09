import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, tokenStore } from '../api/client'
import type { CurrentUser } from '../api/types'

interface AuthContextValue {
  user: CurrentUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, password_confirm: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  const loadMe = async () => {
    try {
      const res = await api.get<CurrentUser>('/auth/me/')
      setUser(res.data)
    } catch {
      setUser(null)
      tokenStore.clear()
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tokenStore.getAccess()) {
      void loadMe()
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login/', { email, password })
    tokenStore.set(res.data.access, res.data.refresh)
    await loadMe()
  }

  const register = async (email: string, password: string, password_confirm: string) => {
    const res = await api.post('/auth/register/', {
      email,
      password,
      password_confirm,
    })
    tokenStore.set(res.data.access, res.data.refresh)
    await loadMe()
  }

  const logout = () => {
    tokenStore.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh: loadMe }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
