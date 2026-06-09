import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const ACCESS_KEY = 'phs.access'
const REFRESH_KEY = 'phs.refresh'

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh?: string) => {
    localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess()
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise

  const refresh = tokenStore.getRefresh()
  if (!refresh) throw new Error('no refresh token')

  refreshPromise = axios
    .post('/api/auth/refresh/', { refresh })
    .then((res) => {
      const access = res.data.access as string
      tokenStore.set(access)
      return access
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retried?: boolean
    }
    const url = original?.url ?? ''
    if (
      error.response?.status === 401 &&
      !original?._retried &&
      !url.includes('/auth/login/') &&
      !url.includes('/auth/refresh/') &&
      !url.includes('/auth/register/')
    ) {
      original._retried = true
      try {
        const access = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      } catch {
        tokenStore.clear()
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  },
)
