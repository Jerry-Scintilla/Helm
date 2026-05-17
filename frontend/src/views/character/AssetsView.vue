<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import AssetItemGroup from '@/components/AssetItemGroup.vue'
import type { AssetNode } from '@/components/AssetItemGroup.vue'

interface LocationGroup {
  location_id: number | null
  location_type: string
  location_name: string | null
  items: AssetNode[]
}

const route = useRoute()
const characterId = Number(route.params.id)

const locations = ref<LocationGroup[]>([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

function countAll(nodes: AssetNode[]): number {
  return nodes.reduce((n, node) => n + 1 + countAll(node.items), 0)
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await api.get(`/api/v1/characters/${characterId}/assets`, {
      params: { q: searchQuery.value || undefined, page: page.value, page_size: pageSize.value },
    })
    locations.value = res.data.locations
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 350)
}

watch(page, load)

function locationLabel(loc: LocationGroup): string {
  if (loc.location_name) return loc.location_name
  if (loc.location_id) return String(loc.location_id)
  return '未知位置'
}

function locationTypeLabel(type: string): string {
  const map: Record<string, string> = {
    station: '空间站',
    solar_system: '星系',
    other: '其他',
    unknown: '未知',
  }
  return map[type] ?? type
}
</script>

<template>
  <div>
    <h1 class="page-title h-serif">资产</h1>

    <!-- 搜索栏 -->
    <div class="toolbar">
      <n-input
        v-model:value="searchQuery"
        placeholder="搜索星系、空间站或玩家建筑…"
        clearable
        class="search-input"
        @input="onSearchInput"
        @clear="() => { page = 1; load() }"
      >
        <template #prefix>
          <n-icon><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></n-icon>
        </template>
      </n-input>
      <span class="total-bar">共 {{ total }} 个地点</span>
    </div>

    <n-spin v-if="loading" :size="24" style="display:block;margin:60px auto;" />
    <div v-else-if="locations.length === 0" class="muted">
      {{ searchQuery ? '未找到匹配的地点' : '暂无资产数据' }}
    </div>

    <div v-else>
      <n-collapse class="location-list" arrow-placement="right">
        <n-collapse-item
          v-for="loc in locations"
          :key="loc.location_id ?? 'unknown'"
          :name="loc.location_id ?? 'unknown'"
        >
          <template #header>
            <span class="loc-header">
              <span class="loc-name">{{ locationLabel(loc) }}</span>
              <span class="loc-type-badge">{{ locationTypeLabel(loc.location_type) }}</span>
            </span>
          </template>
          <template #header-extra>
            <span class="loc-count">{{ countAll(loc.items) }} 项</span>
          </template>

          <div class="col-header">
            <span>物品</span>
            <span style="text-align:right">数量</span>
          </div>
          <AssetItemGroup :items="loc.items" :depth="0" />
        </n-collapse-item>
      </n-collapse>

      <div class="pagination-bar">
        <n-pagination
          v-model:page="page"
          :page-count="Math.ceil(total / pageSize)"
          :page-slot="5"
          show-quick-jumper
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; margin-bottom: 20px; }
.muted { color: #5e5d59; }

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.search-input {
  max-width: 320px;
}
.total-bar {
  font-size: 0.85rem;
  color: #87867f;
  white-space: nowrap;
}

.location-list { margin-bottom: 20px; }

.location-list :deep(.n-collapse-item__header-main) {
  display: flex;
  align-items: center;
  min-width: 0;
  overflow: visible;
}

.loc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.loc-name {
  font-size: 0.92rem;
  color: #faf9f5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.loc-type-badge {
  display: inline-block;
  flex-shrink: 0;
  font-size: 0.72rem;
  color: #87867f;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid #3d3d3a;
  border-radius: 4px;
  padding: 1px 6px;
  white-space: nowrap;
  line-height: 1.4;
}
.loc-count {
  font-size: 0.78rem;
  color: #87867f;
}

.col-header {
  display: grid;
  grid-template-columns: 1fr 60px;
  gap: 8px;
  padding: 4px 12px;
  font-size: 0.75rem;
  color: #5e5d59;
  border-bottom: 1px solid #30302e;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  padding: 16px 0 8px;
}
</style>
