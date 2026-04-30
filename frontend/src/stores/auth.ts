import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import api from '@/api'
import { resetPluginRoutesFlag } from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const characterId = ref<number | null>(
    localStorage.getItem('character_id') ? Number(localStorage.getItem('character_id')) : null
  )
  const characterName = ref<string | null>(localStorage.getItem('character_name'))
  const primaryCharacterId = ref<number | null>(
    localStorage.getItem('primary_character_id') ? Number(localStorage.getItem('primary_character_id')) : null
  )
  const primaryCharacterName = ref<string | null>(localStorage.getItem('primary_character_name'))
  const isSuperuser = ref<boolean>(localStorage.getItem('is_superuser') === 'true')

  const isLoggedIn = computed(() => !!accessToken.value)

  function setTokens(data: {
    access_token: string
    refresh_token: string
    character_id: number
    character_name: string
    primary_character_id?: number
    primary_character_name?: string
    is_superuser?: boolean
  }) {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    characterId.value = data.character_id
    characterName.value = data.character_name
    primaryCharacterId.value = data.primary_character_id ?? data.character_id
    primaryCharacterName.value = data.primary_character_name ?? data.character_name
    isSuperuser.value = data.is_superuser ?? false
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('character_id', String(data.character_id))
    localStorage.setItem('character_name', data.character_name)
    localStorage.setItem('primary_character_id', String(data.primary_character_id ?? data.character_id))
    localStorage.setItem('primary_character_name', data.primary_character_name ?? data.character_name)
    localStorage.setItem('is_superuser', String(data.is_superuser ?? false))
  }

  function updatePrimary(id: number, name: string) {
    primaryCharacterId.value = id
    primaryCharacterName.value = name
    localStorage.setItem('primary_character_id', String(id))
    localStorage.setItem('primary_character_name', name)
  }

  async function bindCharacter(): Promise<string> {
    const { data } = await api.get('/auth/eve/bind')
    return data.redirect_url
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
    primaryCharacterId.value = null
    primaryCharacterName.value = null
    isSuperuser.value = false
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('character_id')
    localStorage.removeItem('character_name')
    localStorage.removeItem('primary_character_id')
    localStorage.removeItem('primary_character_name')
    localStorage.removeItem('is_superuser')
    resetPluginRoutesFlag()
  }

  function loginWithEve() {
    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    window.location.href = `${base}/auth/eve/login`
  }

  return {
    accessToken, refreshToken, characterId, characterName,
    primaryCharacterId, primaryCharacterName,
    isSuperuser, isLoggedIn,
    setTokens, updatePrimary, bindCharacter, logout, loginWithEve,
  }
})
