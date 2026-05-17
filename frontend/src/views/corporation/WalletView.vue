<script setup lang="ts">
import { onMounted, ref, computed, h } from 'vue'
import { useRoute } from 'vue-router'
import { useCorporationStore } from '@/stores/corporation'
import { useI18n } from 'vue-i18n'
import type { DataTableColumns } from 'naive-ui'
import type { CorporationJournalEntry } from '@/stores/corporation'

const route = useRoute()
const corpStore = useCorporationStore()
const { t, te } = useI18n()

function refTypeLabel(type: string): string {
  const key = `wallet.refTypes.${type}`
  return te(key) ? t(key) : type
}
const corporationId = Number(route.params.id)
const loading = ref(true)
const selectedDivision = ref<number>(1)
const journalPage = ref(1)

onMounted(async () => {
  try {
    await corpStore.fetchWallet(corporationId)
    if (corpStore.wallets.length > 0) {
      selectedDivision.value = corpStore.wallets[0]?.wallet_division ?? 1
    }
    await loadJournal()
  } finally {
    loading.value = false
  }
})

async function loadJournal() {
  await corpStore.fetchJournal(corporationId, selectedDivision.value, journalPage.value)
}

function fmt(n: number | null) {
  if (n === null) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}
function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString()
}

const selectedWallet = computed(() =>
  corpStore.wallets.find(w => w.wallet_division === selectedDivision.value)
)

const journalCols: DataTableColumns<CorporationJournalEntry> = [
  { title: () => t('wallet.colDate'), key: 'date', width: 160, render: r => fmtDate(r.date) },
  { title: () => t('wallet.colType'), key: 'ref_type', ellipsis: true, render: r => refTypeLabel(r.ref_type) },
  { title: () => t('wallet.colDesc'), key: 'description', ellipsis: true },
  {
    title: () => t('wallet.colAmount'), key: 'amount', width: 140, align: 'right',
    render: r => h('span', { class: (r.amount ?? 0) >= 0 ? 'pos' : 'neg' }, fmt(r.amount)),
  },
  { title: () => t('wallet.colBalance'), key: 'balance', width: 140, align: 'right', render: r => fmt(r.balance) },
]
</script>

<template>
  <div>
    <h1 class="page-title h-serif">{{ t('corp.wallet') }}</h1>

    <n-spin v-if="loading" :size="24" style="display:block;margin:60px auto;" />
    <template v-else>
      <!-- Division selector -->
      <div class="division-row">
        <n-radio-group v-model:value="selectedDivision" size="small" @update:value="loadJournal">
          <n-radio-button
            v-for="w in corpStore.wallets"
            :key="w.wallet_division"
            :value="w.wallet_division"
          >
            {{ t('corp.division', { n: w.wallet_division }) }}
          </n-radio-button>
        </n-radio-group>
      </div>

      <!-- Balance card -->
      <div v-if="selectedWallet" class="balance-card">
        <div class="balance-label">{{ t('wallet.balance') }}</div>
        <div class="balance-value">{{ fmt(selectedWallet.balance) }} ISK</div>
      </div>

      <!-- Journal -->
      <n-data-table
        :columns="journalCols"
        :data="corpStore.walletJournal"
        :bordered="false"
        size="small"
        :row-key="(r: CorporationJournalEntry) => r.journal_id"
      />
      <div class="pagination">
        <n-button size="small" :disabled="journalPage <= 1" @click="journalPage--; loadJournal()">{{ t('common.prevPage') }}</n-button>
        <span class="page-num">{{ t('common.page', { n: journalPage }) }}</span>
        <n-button size="small" :disabled="corpStore.walletJournal.length < 50" @click="journalPage++; loadJournal()">{{ t('common.nextPage') }}</n-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; margin-bottom: 20px; }
.division-row { margin-bottom: 16px; }
.balance-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 20px;
  display: inline-block;
}
.balance-label { font-size: 0.78rem; color: #87867f; margin-bottom: 6px; }
.balance-value { font-size: 1.4rem; font-weight: 500; color: #faf9f5; }
.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.page-num { font-size: 0.85rem; color: #87867f; }
:deep(.pos) { color: #6abf69; }
:deep(.neg) { color: #d97757; }
</style>
