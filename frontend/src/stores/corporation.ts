import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface CorporationInfo {
  corporation_id: number
  name: string
  ticker: string
  member_count: number
  ceo_id: number | null
  alliance_id: number | null
  description: string
  updated_at: string | null
}

export interface CorporationMember {
  character_id: number
  ship_type_id: number | null
  ship_type_name: string | null
  start_date: string | null
  logon_date: string | null
  logoff_date: string | null
  location_id: number | null
}

export interface CorporationWallet {
  wallet_division: number
  balance: number
  updated_at: string | null
}

export interface CorporationJournalEntry {
  journal_id: number
  date: string | null
  ref_type: string
  first_party_id: number | null
  second_party_id: number | null
  amount: number | null
  balance: number | null
  description: string
}

export interface CorporationAsset {
  item_id: number
  type_id: number
  location_id: number
  location_type: string
  quantity: number
  is_singleton: boolean
}

export const useCorporationStore = defineStore('corporation', () => {
  const corporations = ref<CorporationInfo[]>([])
  const corporationInfo = ref<CorporationInfo | null>(null)
  const members = ref<CorporationMember[]>([])
  const wallets = ref<CorporationWallet[]>([])
  const walletJournal = ref<CorporationJournalEntry[]>([])
  const assets = ref<CorporationAsset[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchList() {
    loading.value = true
    error.value = null
    try {
      const res = await api.get('/api/v1/corporations/')
      corporations.value = res.data
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'Failed to load corporations'
    } finally {
      loading.value = false
    }
  }

  async function fetchInfo(corporationId: number) {
    loading.value = true
    error.value = null
    try {
      const res = await api.get(`/api/v1/corporations/${corporationId}/`)
      corporationInfo.value = res.data
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'Failed to load corporation'
    } finally {
      loading.value = false
    }
  }

  async function fetchMembers(corporationId: number) {
    const res = await api.get(`/api/v1/corporations/${corporationId}/members`)
    members.value = res.data
  }

  async function fetchWallet(corporationId: number) {
    const res = await api.get(`/api/v1/corporations/${corporationId}/wallet`)
    wallets.value = res.data
  }

  async function fetchJournal(corporationId: number, division: number, page = 1) {
    const res = await api.get(`/api/v1/corporations/${corporationId}/wallet/${division}/journal`, { params: { page } })
    walletJournal.value = res.data
  }

  async function fetchAssets(corporationId: number, page = 1) {
    const res = await api.get(`/api/v1/corporations/${corporationId}/assets`, { params: { page } })
    assets.value = res.data
  }

  return {
    corporations, corporationInfo, members, wallets, walletJournal, assets,
    loading, error,
    fetchList, fetchInfo, fetchMembers, fetchWallet, fetchJournal, fetchAssets,
  }
})
