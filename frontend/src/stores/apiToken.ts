import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface APIToken {
  id: number
  name: string
  token_prefix: string
  scopes: string
  expires_at: string | null
  last_used_at: string | null
  is_active: boolean
  created_at: string
}

export interface APITokenCreated extends APIToken {
  token: string
}

export const useApiTokenStore = defineStore('apiToken', () => {
  const tokens = ref<APIToken[]>([])
  const newTokenValue = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchTokens() {
    loading.value = true
    error.value = null
    try {
      const res = await api.get('/api/v1/user/tokens')
      tokens.value = res.data
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'Failed to load tokens'
    } finally {
      loading.value = false
    }
  }

  async function createToken(name: string, scopes: string[]) {
    const res = await api.post('/api/v1/user/tokens', { name, scopes: scopes.join(' ') })
    const created: APITokenCreated = res.data
    newTokenValue.value = created.token
    await fetchTokens()
    return created
  }

  async function revokeToken(tokenId: number) {
    await api.delete(`/api/v1/user/tokens/${tokenId}`)
    await fetchTokens()
  }

  function clearNewToken() {
    newTokenValue.value = null
  }

  return {
    tokens, newTokenValue, loading, error,
    fetchTokens, createToken, revokeToken, clearNewToken,
  }
})
