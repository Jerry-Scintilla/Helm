<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore, type Contract, type ContractDetail } from '@/stores/character'
import { useI18n } from 'vue-i18n'
import type { DataTableColumns } from 'naive-ui'
import { NTag } from 'naive-ui'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const charStore = useCharacterStore()
const { t, te, locale } = useI18n()
const characterId = Number(route.params.id)

const loading = ref(true)
const rows = ref<Contract[]>([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const direction = ref<'all' | 'outgoing' | 'incoming'>('all')

// Detail drawer
const showDetail = ref(false)
const detailLoading = ref(false)
const detail = ref<ContractDetail | null>(null)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await charStore.fetchContracts(characterId, { direction: direction.value, page: page.value })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function changeDirection(d: 'all' | 'outgoing' | 'incoming') {
  if (direction.value === d) return
  direction.value = d
  page.value = 1
  load()
}

function changePage(delta: number) {
  const next = page.value + delta
  if (next < 1 || (next - 1) * perPage >= total.value) return
  page.value = next
  load()
}

async function openDetail(contractId: number) {
  showDetail.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await charStore.fetchContractDetail(characterId, contractId, locale.value)
  } finally {
    detailLoading.value = false
  }
}

function typeLabel(type: string): string {
  const k = `contracts.types.${type}`
  return te(k) ? t(k) : type
}
function statusLabel(status: string): string {
  const k = `contracts.statuses.${status}`
  return te(k) ? t(k) : status
}
function statusTagType(status: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  if (status === 'in_progress') return 'info'
  if (status === 'outstanding') return 'warning'
  if (status.startsWith('finished')) return 'success'
  if (['cancelled', 'rejected', 'failed', 'deleted', 'reversed'].includes(status)) return 'error'
  return 'default'
}
function fmtIsk(n: number | null): string {
  if (!n) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 }) + ' ISK'
}
function fmtNum(n: number | null, suffix = ''): string {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 }) + suffix
}
function fmtDate(dt: string | null): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleString()
}
function priceReward(c: Contract): string {
  if (c.price) return fmtIsk(c.price)
  if (c.reward) return '+' + fmtIsk(c.reward)
  return '—'
}

const cols: DataTableColumns<Contract> = [
  {
    title: () => t('contracts.type'), key: 'type', width: 96,
    render: r => h(NTag, { size: 'small', bordered: false }, { default: () => typeLabel(r.type) }),
  },
  {
    title: () => t('contracts.title'), key: 'title', ellipsis: { tooltip: true },
    render: r => r.title || t('contracts.noTitle'),
  },
  { title: () => t('contracts.from'), key: 'issuer_name', ellipsis: true, render: r => r.issuer_name || '—' },
  { title: () => t('contracts.to'), key: 'assignee_name', ellipsis: true, render: r => r.assignee_name || '—' },
  { title: () => t('contracts.price'), key: 'price', width: 150, align: 'right', render: priceReward },
  {
    title: () => t('contracts.status'), key: 'status', width: 96,
    render: r => h(NTag, { size: 'small', type: statusTagType(r.status), bordered: false }, { default: () => statusLabel(r.status) }),
  },
  { title: () => t('contracts.expired'), key: 'date_expired', width: 160, render: r => fmtDate(r.date_expired) },
]

function rowProps(row: Contract) {
  return { style: 'cursor: pointer', onClick: () => openDetail(row.contract_id) }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title h-serif">{{ t('nav.contracts') }}</h1>
      <n-button-group size="small">
        <n-button :type="direction === 'all' ? 'primary' : 'default'" @click="changeDirection('all')">{{ t('contracts.direction.all') }}</n-button>
        <n-button :type="direction === 'outgoing' ? 'primary' : 'default'" @click="changeDirection('outgoing')">{{ t('contracts.direction.outgoing') }}</n-button>
        <n-button :type="direction === 'incoming' ? 'primary' : 'default'" @click="changeDirection('incoming')">{{ t('contracts.direction.incoming') }}</n-button>
      </n-button-group>
    </div>

    <div v-if="loading" class="helm-section-loader"><HelmLoader :size="36" /></div>
    <template v-else>
      <n-data-table
        :columns="cols"
        :data="rows"
        :bordered="false"
        size="small"
        :row-key="(r: Contract) => r.contract_id"
        :row-props="rowProps"
      />
      <div v-if="rows.length === 0" class="muted">{{ t('contracts.empty') }}</div>
      <div class="pagination">
        <n-button size="small" :disabled="page <= 1" @click="changePage(-1)">{{ t('common.prevPage') }}</n-button>
        <span class="page-num">{{ t('common.page', { n: page }) }} · {{ total }}</span>
        <n-button size="small" :disabled="page * perPage >= total" @click="changePage(1)">{{ t('common.nextPage') }}</n-button>
      </div>
    </template>

    <!-- Detail drawer -->
    <n-drawer v-model:show="showDetail" :width="460" placement="right">
      <n-drawer-content :title="detail?.title || t('contracts.noTitle')" closable>
        <div v-if="detailLoading" class="helm-section-loader"><HelmLoader :size="32" /></div>
        <template v-else-if="detail">
          <div class="d-fields">
            <div class="d-field"><span>{{ t('contracts.type') }}</span><span>{{ typeLabel(detail.type) }}</span></div>
            <div class="d-field"><span>{{ t('contracts.status') }}</span><span>{{ statusLabel(detail.status) }}</span></div>
            <div class="d-field"><span>{{ t('contracts.from') }}</span><span>{{ detail.issuer_name || '—' }}</span></div>
            <div class="d-field"><span>{{ t('contracts.to') }}</span><span>{{ detail.assignee_name || '—' }}</span></div>
            <div v-if="detail.acceptor_name" class="d-field"><span>{{ t('contracts.acceptor') }}</span><span>{{ detail.acceptor_name }}</span></div>
            <div v-if="detail.price" class="d-field"><span>{{ t('contracts.price') }}</span><span>{{ fmtIsk(detail.price) }}</span></div>
            <div v-if="detail.reward" class="d-field"><span>{{ t('contracts.reward') }}</span><span>{{ fmtIsk(detail.reward) }}</span></div>
            <div v-if="detail.collateral" class="d-field"><span>{{ t('contracts.collateral') }}</span><span>{{ fmtIsk(detail.collateral) }}</span></div>
            <div v-if="detail.buyout" class="d-field"><span>{{ t('contracts.buyout') }}</span><span>{{ fmtIsk(detail.buyout) }}</span></div>
            <div v-if="detail.volume" class="d-field"><span>{{ t('contracts.volume') }}</span><span>{{ fmtNum(detail.volume, ' m³') }}</span></div>
            <div v-if="detail.start_location_name" class="d-field"><span>{{ t('contracts.fromLocation') }}</span><span>{{ detail.start_location_name }}</span></div>
            <div v-if="detail.end_location_name" class="d-field"><span>{{ t('contracts.toLocation') }}</span><span>{{ detail.end_location_name }}</span></div>
            <div class="d-field"><span>{{ t('contracts.issued') }}</span><span>{{ fmtDate(detail.date_issued) }}</span></div>
            <div class="d-field"><span>{{ t('contracts.expired') }}</span><span>{{ fmtDate(detail.date_expired) }}</span></div>
          </div>

          <div v-if="detail.items.length" class="d-items">
            <div class="d-section-title">{{ t('contracts.items') }}</div>
            <div v-for="(it, i) in detail.items" :key="i" class="d-item" :class="{ requested: !it.is_included }">
              <img v-if="it.icon_url" :src="it.icon_url" class="d-item-icon" alt="" />
              <span class="d-item-name">{{ it.type_name }}</span>
              <span class="d-item-tag">{{ it.is_included ? t('contracts.included') : t('contracts.requested') }}</span>
              <span v-if="it.quantity" class="d-item-qty">× {{ it.quantity.toLocaleString() }}</span>
            </div>
          </div>

          <div v-if="detail.bids.length" class="d-items">
            <div class="d-section-title">{{ t('contracts.bids') }}</div>
            <div v-for="(b, i) in detail.bids" :key="i" class="d-item">
              <span class="d-item-name">{{ fmtIsk(b.amount) }}</span>
              <span class="d-item-qty">{{ fmtDate(b.date_bid) }}</span>
            </div>
          </div>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 1.6rem; color: #faf9f5; margin: 0; }
.muted { padding: 24px 4px; color: #5e5d59; font-size: 0.9rem; }
.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.page-num { font-size: 0.85rem; color: #87867f; }

.d-fields { display: flex; flex-direction: column; gap: 8px; }
.d-field { display: flex; justify-content: space-between; gap: 16px; font-size: 0.85rem; border-bottom: 1px solid #2a2a28; padding-bottom: 8px; }
.d-field > span:first-child { color: #87867f; flex-shrink: 0; }
.d-field > span:last-child { color: #b0aea5; text-align: right; word-break: break-word; }

.d-items { margin-top: 18px; }
.d-section-title { font-size: 0.8rem; color: #87867f; margin-bottom: 8px; }
.d-item { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #b0aea5; padding: 4px 0; }
.d-item.requested { opacity: 0.65; }
.d-item-icon { width: 24px; height: 24px; border-radius: 4px; }
.d-item-name { flex: 1; }
.d-item-tag { font-size: 0.7rem; color: #5e5d59; }
.d-item-qty { color: #87867f; }
</style>
