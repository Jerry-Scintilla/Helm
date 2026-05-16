<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import api from '@/api'

const message = useMessage()

// ── Region data ──────────────────────────────────────────────────────────────
const KNOWN_REGIONS: { label: string; value: number }[] = [
  { label: 'The Forge（吉他 Jita）',         value: 10000002 },
  { label: 'Domain（阿马尔 Amarr）',          value: 10000043 },
  { label: 'Sinq Laison（都尔西 Dodixie）',   value: 10000032 },
  { label: 'Metropolis（海克 Hek）',          value: 10000042 },
  { label: 'Heimatar（鲁恩斯 Rens）',         value: 10000030 },
  { label: 'Delve',                           value: 10000060 },
  { label: 'Catch',                           value: 10000014 },
  { label: 'Vale of the Silent',              value: 10000003 },
]

function regionName(id: number | null): string {
  if (id === null) return '—'
  return KNOWN_REGIONS.find(r => r.value === id)?.label ?? `Region ${id}`
}

// ── Config ───────────────────────────────────────────────────────────────────
const configLoading = ref(true)
const configSaving  = ref(false)
const currentRegionId = ref<number | null>(null)
const selectedRegionId = ref<number | null>(null)

async function fetchConfig() {
  configLoading.value = true
  try {
    const { data } = await api.get('/api/v1/admin/market/config')
    currentRegionId.value  = data.region_id
    selectedRegionId.value = data.region_id
  } catch {
    message.error('获取市场配置失败')
  } finally {
    configLoading.value = false
  }
}

async function saveConfig() {
  if (!selectedRegionId.value) {
    message.warning('请选择一个星域')
    return
  }
  configSaving.value = true
  try {
    await api.put('/api/v1/admin/market/config', { region_id: selectedRegionId.value })
    currentRegionId.value = selectedRegionId.value
    message.success('市场默认区域已更新')
  } catch (e: any) {
    message.error(e.response?.data?.detail ?? '保存失败')
  } finally {
    configSaving.value = false
  }
}

const configDirty = computed(() => selectedRegionId.value !== currentRegionId.value)

// ── Price Query ───────────────────────────────────────────────────────────────
interface PriceRow {
  type_id:   number
  type_name: string | null
  best_buy:  number | null
  best_sell: number | null
}

const querying       = ref(false)
const fetchingRandom = ref(false)
const queryRegionUsed = ref<number | null>(null)
const queryResult    = ref<PriceRow | null>(null)
const queryError     = ref('')

function formatISK(v: number | null): string {
  if (v === null) return '—'
  if (v >= 1_000_000_000) return (v / 1_000_000_000).toFixed(2) + ' B ISK'
  if (v >= 1_000_000)     return (v / 1_000_000).toFixed(2)     + ' M ISK'
  if (v >= 1_000)         return (v / 1_000).toFixed(2)         + ' K ISK'
  return v.toFixed(2) + ' ISK'
}

async function runRandomQuery() {
  queryError.value  = ''
  queryResult.value = null
  fetchingRandom.value = true
  querying.value = true
  try {
    // 1. 随机取一个物品
    const { data: item } = await api.get('/api/v1/market/random-item')
    fetchingRandom.value = false

    // 2. 查询该物品价格
    const { data } = await api.get('/api/v1/market/prices', {
      params: { type_ids: String(item.type_id) },
    })
    queryRegionUsed.value = data.region_id
    const row = data.prices[String(item.type_id)]
    queryResult.value = row ?? null
    if (!row) queryError.value = '该物品在目标区域暂无挂单'
  } catch (e: any) {
    queryError.value = e.response?.data?.detail ?? '查询失败'
  } finally {
    fetchingRandom.value = false
    querying.value = false
  }
}

onMounted(fetchConfig)
</script>

<template>
  <div class="market-root">

    <!-- ── Region Config ──────────────────────────────────────────────────── -->
    <section class="panel">
      <div class="panel-header">
        <span class="panel-title h-serif">默认查询星域</span>
        <n-button size="small" :loading="configLoading" @click="fetchConfig">刷新</n-button>
      </div>

      <n-spin v-if="configLoading" :size="20" style="display:block;margin:32px auto;" />

      <template v-else>
        <div class="config-body">
          <div class="current-region-row">
            <span class="field-label">当前生效</span>
            <span class="region-badge">{{ regionName(currentRegionId) }}</span>
          </div>

          <div class="select-row">
            <div class="select-wrap">
              <span class="field-label">选择或搜索星域</span>
              <n-select
                v-model:value="selectedRegionId"
                :options="KNOWN_REGIONS"
                filterable
                placeholder="输入星域名称搜索..."
                size="small"
                class="region-select"
              />
            </div>
            <n-button
              class="action-btn"
              :loading="configSaving"
              :disabled="configSaving || !configDirty"
              @click="saveConfig"
            >保存</n-button>
          </div>
        </div>
      </template>
    </section>

    <!-- ── Random Price Query ─────────────────────────────────────────────── -->
    <section class="panel">
      <div class="panel-header">
        <span class="panel-title h-serif">物价随机检索</span>
        <span class="panel-sub">随机从 SDE 抽取一个可交易物品，查询当前最优买卖价</span>
      </div>

      <div class="query-body">
        <n-button
          class="action-btn random-btn"
          :loading="querying"
          @click="runRandomQuery"
        >
          {{ fetchingRandom ? '正在随机选取...' : querying ? '查询中...' : '随机查询物价' }}
        </n-button>

        <div v-if="queryError" class="error-box">{{ queryError }}</div>

        <div v-if="queryResult" class="result-card">
          <div class="result-item-header">
            <div class="result-type-id">type_id · {{ queryResult.type_id }}</div>
            <div class="result-type-name">{{ queryResult.type_name ?? '未知物品' }}</div>
            <div class="result-region">
              查询星域：{{ regionName(queryRegionUsed) }}
            </div>
          </div>

          <div class="price-row-grid">
            <div class="price-block buy">
              <div class="price-label">最优买价</div>
              <div class="price-value">{{ formatISK(queryResult.best_buy) }}</div>
              <div class="price-hint">买单最高价</div>
            </div>
            <div class="price-divider"></div>
            <div class="price-block sell">
              <div class="price-label">最优卖价</div>
              <div class="price-value">{{ formatISK(queryResult.best_sell) }}</div>
              <div class="price-hint">卖单最低价</div>
            </div>
            <div class="price-divider"></div>
            <div class="price-block spread">
              <div class="price-label">价差</div>
              <div class="price-value">
                <template v-if="queryResult.best_buy !== null && queryResult.best_sell !== null">
                  {{ formatISK(queryResult.best_sell - queryResult.best_buy) }}
                </template>
                <template v-else>—</template>
              </div>
              <div class="price-hint">卖价 − 买价</div>
            </div>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<style scoped>
.market-root { display: flex; flex-direction: column; gap: 20px; }

/* Panel */
.panel {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 12px;
  overflow: hidden;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid #30302e;
  background: rgba(255,255,255,0.02);
}
.panel-title {
  font-size: 0.95rem;
  font-weight: 500;
  color: #faf9f5;
  letter-spacing: 0.01em;
  flex-shrink: 0;
}
.panel-sub {
  font-size: 0.78rem;
  color: #5e5d59;
}
/* push refresh button to right */
.panel-header > .n-button { margin-left: auto; }

/* Config body */
.config-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.current-region-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.region-badge {
  background: rgba(201,100,66,0.12);
  border: 1px solid rgba(201,100,66,0.3);
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 0.85rem;
  color: #d97757;
  font-family: Georgia, serif;
}
.select-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.select-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.region-select { width: 100%; }

.field-label {
  font-size: 0.72rem;
  color: #5e5d59;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* Query body */
.query-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.random-btn { width: fit-content; }

/* Result card */
.result-card {
  background: #181816;
  border: 1px solid #30302e;
  border-radius: 10px;
  overflow: hidden;
}
.result-item-header {
  padding: 16px 20px 14px;
  border-bottom: 1px solid #30302e;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.result-type-id {
  font-size: 0.72rem;
  color: #5e5d59;
  font-family: monospace;
  letter-spacing: 0.04em;
}
.result-type-name {
  font-size: 1.2rem;
  font-weight: 500;
  color: #faf9f5;
  font-family: Georgia, serif;
  line-height: 1.2;
}
.result-region {
  font-size: 0.78rem;
  color: #3d3d3a;
  margin-top: 2px;
}

.price-row-grid {
  display: flex;
  align-items: stretch;
}
.price-block {
  flex: 1;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.price-divider {
  width: 1px;
  background: #30302e;
  margin: 14px 0;
}
.price-label {
  font-size: 0.72rem;
  color: #5e5d59;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.price-value {
  font-size: 1.15rem;
  font-weight: 500;
  font-family: Georgia, serif;
  line-height: 1.2;
}
.buy  .price-value { color: #6abf69; }
.sell .price-value { color: #d97757; }
.spread .price-value { color: #b0aea5; }
.price-hint { font-size: 0.72rem; color: #3d3d3a; }

/* Error */
.error-box {
  background: rgba(181,51,51,0.1);
  border: 1px solid #b53333;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 0.85rem;
  color: #faf9f5;
}

/* Action button */
.action-btn {
  background: #c96442 !important;
  color: #faf9f5 !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 0 18px !important;
  font-size: 0.88rem !important;
  height: 34px !important;
  transition: opacity 0.15s !important;
}
.action-btn:hover:not(:disabled) { opacity: 0.88 !important; }
.action-btn:disabled { background: #3d3d3a !important; color: #5e5d59 !important; cursor: not-allowed; }
</style>
