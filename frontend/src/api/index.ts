import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 15000,
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Shared token refresh ─────────────────────────────────────────────────────
// Dedupes concurrent refresh calls from both the axios 401 interceptor and
// iframe plugins (via helm:token:expired). On success returns the new access
// token; on failure clears auth state and redirects to /login.

let refreshPromise: Promise<string> | null = null
const tokenListeners = new Set<(token: string) => void>()

export function onAccessTokenRefreshed(cb: (token: string) => void): () => void {
  tokenListeners.add(cb)
  return () => tokenListeners.delete(cb)
}

export function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) throw new Error('No refresh token')

    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    try {
      const { data } = await axios.post(`${base}/api/v1/auth/token/refresh`, {
        refresh_token: refreshToken,
      })
      const newToken = data.access_token as string
      localStorage.setItem('access_token', newToken)
      tokenListeners.forEach((cb) => {
        try { cb(newToken) } catch {}
      })
      return newToken
    } catch (err) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      throw err
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

// On 401: refresh token then retry
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    original._retry = true
    try {
      const newToken = await refreshAccessToken()
      original.headers.Authorization = `Bearer ${newToken}`
      return api(original)
    } catch {
      return Promise.reject(error)
    }
  }
)

export default api
