import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface AllianceInfo {
  alliance_id: number
  name: string
  ticker: string
  creator_corp_id: number | null
  executor_corp_id: number | null
  updated_at: string | null
  member_corporations: number[]
}

export const useAllianceStore = defineStore('alliance', () => {
  const allianceInfo = ref<AllianceInfo | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchInfo(allianceId: number) {
    loading.value = true
    error.value = null
    try {
      const res = await api.get(`/api/v1/alliances/${allianceId}/`)
      allianceInfo.value = res.data
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'Failed to load alliance'
    } finally {
      loading.value = false
    }
  }

  return { allianceInfo, loading, error, fetchInfo }
})
