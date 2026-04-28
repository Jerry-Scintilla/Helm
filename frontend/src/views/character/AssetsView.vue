<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import type { SdeName } from '@/utils/sde'
import { resolveSdeName } from '@/utils/sde'

interface Asset {
  item_id: number
  type_id: number
  type_name?: SdeName | null
  location_id: number
  location_type: string
  location_name: string | null
  quantity: number
  is_singleton: boolean
}

const route = useRoute()
const characterId = Number(route.params.id)
const assets = ref<Asset[]>([])
const loading = ref(true)
const page = ref(1)

// Group by location
const grouped = computed(() => {
  const map = new Map<number, Asset[]>()
  for (const a of assets.value) {
    if (!map.has(a.location_id)) map.set(a.location_id, [])
    map.get(a.location_id)!.push(a)
  }
  return Array.from(map.entries()).map(([loc, items]) => ({
    loc,
    items,
    label: items[0]?.location_name ?? String(loc),
  }))
})

onMounted(() => load())

async function load() {
  loading.value = true
  try {
    const res = await api.get(`/api/v1/characters/${characterId}/assets`, { params: { page: page.value, per_page: 200 } })
    assets.value = res.data
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="page-title h-serif">资产</h1>

    <n-spin v-if="loading" :size="24" style="display:block;margin:60px auto;" />
    <div v-else-if="assets.length === 0" class="muted">暂无资产数据</div>

    <div v-else>
      <div class="total-bar">共 {{ assets.length }} 条资产记录，{{ grouped.length }} 个地点</div>
      <n-collapse class="location-list" arrow-placement="right">
        <n-collapse-item
          v-for="group in grouped"
          :key="group.loc"
          :title="group.label"
          :name="group.loc"
        >
          <template #header-extra>
            <span class="loc-count">{{ group.items.length }} 项</span>
          </template>
          <div class="asset-table">
            <div class="asset-row header-row">
              <span>物品</span>
              <span>数量</span>
              <span>位置类型</span>
            </div>
            <div
              v-for="item in group.items"
              :key="item.item_id"
              class="asset-row"
            >
              <span class="type-name">{{ resolveSdeName(item.type_name, String(item.type_id)) }}</span>
              <span>{{ item.is_singleton ? '1 (singleton)' : item.quantity }}</span>
              <span class="loc-type">{{ item.location_type }}</span>
            </div>
          </div>
        </n-collapse-item>
      </n-collapse>

      <div class="pagination">
        <n-button size="small" :disabled="page <= 1" @click="page--; load()">上一页</n-button>
        <span class="page-num">第 {{ page }} 页</span>
        <n-button size="small" :disabled="assets.length < 200" @click="page++; load()">下一页</n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; margin-bottom: 20px; }
.muted { color: #5e5d59; }
.total-bar { font-size: 0.85rem; color: #87867f; margin-bottom: 16px; }
.loc-count { font-size: 0.78rem; color: #87867f; }

.location-list { margin-bottom: 20px; }

.asset-table { border-top: 1px solid #30302e; }
.asset-row {
  display: grid;
  grid-template-columns: 1fr 80px 120px;
  gap: 8px;
  padding: 6px 12px;
  font-size: 0.85rem;
  color: #b0aea5;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.header-row { color: #5e5d59; font-size: 0.78rem; }
.type-name { color: #faf9f5; }
.loc-type { color: #87867f; }

.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.page-num { font-size: 0.85rem; color: #87867f; }
</style>
