import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import type { SdeName } from '@/utils/sde'

export type ExtensionWidgetType = 'markdown' | 'stats' | 'iframe'

export interface CharacterExtension {
  plugin_name: string
  title: string
  widget: ExtensionWidgetType
  content: any  // markdown: string, stats: Array<{label: string, value: any}>, iframe: {url: string, height?: number}
  order: number
  css_class: string
}

export interface CharacterInfo {
  character_id: number
  character_name: string
  corporation_id: number | null
  corporation_name: string | null
  alliance_id: number | null
  alliance_name: string | null
  scopes: string
  updated_at: string | null
  extensions?: CharacterExtension[]
}

export interface WalletInfo {
  balance: number | null
  updated_at: string | null
}

export interface SkillEntry {
  skill_id: number
  trained_skill_level: number
  skillpoints_in_skill: number
  skill_name?: SdeName | null
}

export interface SkillGroup {
  group_id: number
  group_name: SdeName | null
  skills: SkillEntry[]
}

export interface SkillsInfo {
  total_sp: number
  groups: SkillGroup[]
  updated_at: string | null
}

export interface WalletJournalEntry {
  id: number
  journal_id: number
  date: string | null
  ref_type: string
  first_party_id: number | null
  second_party_id: number | null
  amount: number | null
  balance: number | null
  description: string
}

export interface WalletTransaction {
  transaction_id: number
  date: string | null
  type_id: number
  type_name?: SdeName | null
  location_id: number
  unit_price: number
  quantity: number
  client_id: number | null
  is_buy: boolean
}

export interface SkillQueueEntry {
  queue_position: number
  skill_id: number
  skill_name?: SdeName | null
  finished_level: number
  start_date: string | null
  finish_date: string | null
  level_start_sp: number | null
  level_end_sp: number | null
}

export interface MailItem {
  mail_id: number
  subject: string
  from_id: number | null
  from_name: string | null
  timestamp: string | null
  is_read: boolean
}

export interface MailDetail extends MailItem {
  body: string
}

export interface Notification {
  notification_id: number
  type: string
  sender_id: number | null
  sender_type: string | null
  sender_name: string | null
  timestamp: string | null
  is_read: boolean
  text: string
}

export const useCharacterStore = defineStore('character', () => {
  const characterInfo = ref<CharacterInfo | null>(null)
  const wallet = ref<WalletInfo | null>(null)
  const skills = ref<SkillsInfo | null>(null)
  const walletJournal = ref<WalletJournalEntry[]>([])
  const walletTransactions = ref<WalletTransaction[]>([])
  const skillQueue = ref<SkillQueueEntry[]>([])
  const mails = ref<MailItem[]>([])
  const selectedMail = ref<MailDetail | null>(null)
  const notifications = ref<Notification[]>([])
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

  async function fetchWalletJournal(characterId: number, page = 1) {
    const res = await api.get(`/api/v1/characters/${characterId}/wallet/journal`, { params: { page, per_page: 50 } })
    walletJournal.value = res.data
  }

  async function fetchWalletTransactions(characterId: number, page = 1) {
    const res = await api.get(`/api/v1/characters/${characterId}/wallet/transactions`, { params: { page, per_page: 50 } })
    walletTransactions.value = res.data
  }

  async function fetchSkillQueue(characterId: number) {
    const res = await api.get(`/api/v1/characters/${characterId}/skillqueue`)
    skillQueue.value = res.data
  }

  async function fetchMails(characterId: number) {
    const res = await api.get(`/api/v1/characters/${characterId}/mail`)
    mails.value = res.data
  }

  async function fetchMailBody(characterId: number, mailId: number) {
    const res = await api.get(`/api/v1/characters/${characterId}/mail/${mailId}`)
    selectedMail.value = res.data
  }

  async function fetchNotifications(characterId: number, unreadOnly = false) {
    const res = await api.get(`/api/v1/characters/${characterId}/notifications`, { params: { unread_only: unreadOnly } })
    notifications.value = res.data
  }

  return {
    characterInfo, wallet, skills,
    walletJournal, walletTransactions, skillQueue,
    mails, selectedMail, notifications,
    loading, error,
    fetchAll, fetchWalletJournal, fetchWalletTransactions,
    fetchSkillQueue, fetchMails, fetchMailBody, fetchNotifications,
  }
})
