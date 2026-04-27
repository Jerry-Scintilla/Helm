import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const characterId = ref<number | null>(
    localStorage.getItem('character_id') ? Number(localStorage.getItem('character_id')) : null
  )
  const characterName = ref<string | null>(localStorage.getItem('character_name'))

  const isLoggedIn = computed(() => !!accessToken.value)

  function setTokens(data: {
    access_token: string
    refresh_token: string
    character_id: number
    character_name: string
  }) {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    characterId.value = data.character_id
    characterName.value = data.character_name
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('character_id', String(data.character_id))
    localStorage.setItem('character_name', data.character_name)
  }

  async function logout() {
    if (refreshToken.value) {
      try {
        const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
        await axios.post(`${base}/auth/logout`, { refresh_token: refreshToken.value })
      } catch {}
    }
    accessToken.value = null
    refreshToken.value = null
    characterId.value = null
    characterName.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('character_id')
    localStorage.removeItem('character_name')
  }

  function loginWithEve() {
    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    window.location.href = `${base}/auth/eve/login`
  }

  return { accessToken, refreshToken, characterId, characterName, isLoggedIn, setTokens, logout, loginWithEve }
})
