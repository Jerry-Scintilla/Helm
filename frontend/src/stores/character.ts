import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

interface CharacterInfo {
  character_id: number
  character_name: string
  corporation_id: number | null
  alliance_id: number | null
  updated_at: string | null
}

interface WalletInfo {
  balance: number | null
  updated_at: string | null
}

interface SkillsInfo {
  total_sp: number
  skills: Array<{ skill_id: number; trained_skill_level: number; skillpoints_in_skill: number }>
  updated_at: string | null
}

export const useCharacterStore = defineStore('character', () => {
  const characterInfo = ref<CharacterInfo | null>(null)
  const wallet = ref<WalletInfo | null>(null)
  const skills = ref<SkillsInfo | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll(characterId: number) {
    loading.value = true
    error.value = null
    try {
      const [infoRes, walletRes, skillsRes] = await Promise.all([
        api.get(`/api/v1/characters/${characterId}/`),
        api.get(`/api/v1/characters/${characterId}/wallet`),
        api.get(`/api/v1/characters/${characterId}/skills`),
      ])
      characterInfo.value = infoRes.data
      wallet.value = walletRes.data
      skills.value = skillsRes.data
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'Failed to load character data'
    } finally {
      loading.value = false
    }
  }

  return { characterInfo, wallet, skills, loading, error, fetchAll }
})
