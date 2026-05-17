<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '@/stores/character'
import { useI18n } from 'vue-i18n'
import type { DataTableColumns } from 'naive-ui'
import type { WalletJournalEntry, WalletTransaction } from '@/stores/character'
import { resolveSdeName } from '@/utils/sde'

const route = useRoute()
const charStore = useCharacterStore()
const { t } = useI18n()
const characterId = Number(route.params.id)
const tab = ref<'journal' | 'transactions'>('journal')
const journalPage = ref(1)
const txPage = ref(1)
const loading = ref(false)

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    await Promise.all([
      charStore.fetchWalletJournal(characterId, journalPage.value),
      charStore.fetchWalletTransactions(characterId, txPage.value),
    ])
  } finally {
    loading.value = false
  }
}

function fmt(n: number | null) {
  if (n === null) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}
function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString()
}

const journalCols: DataTableColumns<WalletJournalEntry> = [
  { title: () => t('wallet.colDate'), key: 'date', width: 160, render: r => fmtDate(r.date) },
  { title: () => t('wallet.colType'), key: 'ref_type', ellipsis: true },
  { title: () => t('wallet.colDesc'), key: 'description', ellipsis: true },
  {
    title: () => t('wallet.colAmount'), key: 'amount', width: 140, align: 'right',
    render: r => h('span', { class: (r.amount ?? 0) >= 0 ? 'pos' : 'neg' }, fmt(r.amount)),
  },
  {
    title: () => t('wallet.colBalance'), key: 'balance', width: 140, align: 'right',
    render: r => fmt(r.balance),
  },
]

const txCols: DataTableColumns<WalletTransaction> = [
  { title: () => t('wallet.colDate'), key: 'date', width: 160, render: r => fmtDate(r.date) },
  { title: () => t('wallet.colItem'), key: 'type_id', ellipsis: true, render: r => resolveSdeName(r.type_name, String(r.type_id)) },
  { title: () => t('wallet.colQty'), key: 'quantity', width: 80, align: 'right' },
  { title: () => t('wallet.colPrice'), key: 'unit_price', width: 130, align: 'right', render: r => fmt(r.unit_price) },
  {
    title: () => t('wallet.colDir'), key: 'is_buy', width: 70,
    render: r => h('span', { class: r.is_buy ? 'neg' : 'pos' }, r.is_buy ? t('wallet.buy') : t('wallet.sell')),
  },
]
</script>

<template>
  <div>
    <h1 class="page-title h-serif" style="margin-bottom:20px">{{ t('nav.wallet') }}</h1>

    <n-tabs v-model:value="tab" type="line" animated>
      <n-tab-pane name="journal" :tab="t('wallet.journal')">
        <n-spin v-if="loading" :size="20" style="display:block;margin:40px auto;" />
        <n-data-table
          v-else
          :columns="journalCols"
          :data="charStore.walletJournal"
          :bordered="false"
          size="small"
          :row-key="(r: WalletJournalEntry) => r.journal_id"
        />
        <div class="pagination">
          <n-button size="small" :disabled="journalPage <= 1" @click="journalPage--; charStore.fetchWalletJournal(characterId, journalPage)">{{ t('common.prevPage') }}</n-button>
          <span class="page-num">{{ t('common.page', { n: journalPage }) }}</span>
          <n-button size="small" :disabled="charStore.walletJournal.length < 50" @click="journalPage++; charStore.fetchWalletJournal(characterId, journalPage)">{{ t('common.nextPage') }}</n-button>
        </div>
      </n-tab-pane>

      <n-tab-pane name="transactions" :tab="t('wallet.transactions')">
        <n-spin v-if="loading" :size="20" style="display:block;margin:40px auto;" />
        <n-data-table
          v-else
          :columns="txCols"
          :data="charStore.walletTransactions"
          :bordered="false"
          size="small"
          :row-key="(r: WalletTransaction) => r.transaction_id"
        />
        <div class="pagination">
          <n-button size="small" :disabled="txPage <= 1" @click="txPage--; charStore.fetchWalletTransactions(characterId, txPage)">{{ t('common.prevPage') }}</n-button>
          <span class="page-num">{{ t('common.page', { n: txPage }) }}</span>
          <n-button size="small" :disabled="charStore.walletTransactions.length < 50" @click="txPage++; charStore.fetchWalletTransactions(characterId, txPage)">{{ t('common.nextPage') }}</n-button>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; }
.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.page-num { font-size: 0.85rem; color: #87867f; }
:deep(.pos) { color: #6abf69; }
:deep(.neg) { color: #d97757; }
</style>
