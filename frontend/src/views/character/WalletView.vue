<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '@/stores/character'
import type { DataTableColumns } from 'naive-ui'
import type { WalletJournalEntry, WalletTransaction } from '@/stores/character'

const route = useRoute()
const charStore = useCharacterStore()
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
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}
function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('zh-CN')
}

const journalCols: DataTableColumns<WalletJournalEntry> = [
  { title: '日期', key: 'date', width: 160, render: r => fmtDate(r.date) },
  { title: '类型', key: 'ref_type', ellipsis: true },
  { title: '描述', key: 'description', ellipsis: true },
  {
    title: '金额', key: 'amount', width: 140, align: 'right',
    render: r => h('span', { class: (r.amount ?? 0) >= 0 ? 'pos' : 'neg' }, fmt(r.amount)),
  },
  {
    title: '余额', key: 'balance', width: 140, align: 'right',
    render: r => fmt(r.balance),
  },
]

const txCols: DataTableColumns<WalletTransaction> = [
  { title: '日期', key: 'date', width: 160, render: r => fmtDate(r.date) },
  { title: 'Type ID', key: 'type_id', width: 90 },
  { title: '数量', key: 'quantity', width: 80, align: 'right' },
  { title: '单价', key: 'unit_price', width: 130, align: 'right', render: r => fmt(r.unit_price) },
  {
    title: '方向', key: 'is_buy', width: 70,
    render: r => h('span', { class: r.is_buy ? 'neg' : 'pos' }, r.is_buy ? '买入' : '卖出'),
  },
]
</script>

<template>
  <div>
    <h1 class="page-title h-serif" style="margin-bottom:20px">钱包</h1>

    <n-tabs v-model:value="tab" type="line" animated>
      <n-tab-pane name="journal" tab="流水账">
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
          <n-button size="small" :disabled="journalPage <= 1" @click="journalPage--; charStore.fetchWalletJournal(characterId, journalPage)">上一页</n-button>
          <span class="page-num">第 {{ journalPage }} 页</span>
          <n-button size="small" :disabled="charStore.walletJournal.length < 50" @click="journalPage++; charStore.fetchWalletJournal(characterId, journalPage)">下一页</n-button>
        </div>
      </n-tab-pane>

      <n-tab-pane name="transactions" tab="交易记录">
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
          <n-button size="small" :disabled="txPage <= 1" @click="txPage--; charStore.fetchWalletTransactions(characterId, txPage)">上一页</n-button>
          <span class="page-num">第 {{ txPage }} 页</span>
          <n-button size="small" :disabled="charStore.walletTransactions.length < 50" @click="txPage++; charStore.fetchWalletTransactions(characterId, txPage)">下一页</n-button>
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
