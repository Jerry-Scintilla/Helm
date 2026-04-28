<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useCorporationStore } from '@/stores/corporation'
import type { DataTableColumns } from 'naive-ui'
import type { CorporationAsset } from '@/stores/corporation'
import { resolveSdeName } from '@/utils/sde'

const route = useRoute()
const corpStore = useCorporationStore()
const corporationId = Number(route.params.id)
const loading = ref(true)
const page = ref(1)

onMounted(() => load())

async function load() {
  loading.value = true
  try {
    await corpStore.fetchAssets(corporationId, page.value)
  } finally {
    loading.value = false
  }
}

const cols: DataTableColumns<CorporationAsset> = [
  { title: '物品', key: 'type_id', ellipsis: true, render: r => resolveSdeName(r.type_name, String(r.type_id)) },
  { title: 'Location ID', key: 'location_id', width: 120 },
  { title: '位置类型', key: 'location_type', width: 120 },
  { title: '数量', key: 'quantity', width: 80, align: 'right' },
  {
    title: '状态', key: 'is_singleton', width: 80,
    render: r => r.is_singleton ? 'Singleton' : '—',
  },
]
</script>

<template>
  <div>
    <h1 class="page-title h-serif">公司资产</h1>

    <n-spin v-if="loading" :size="24" style="display:block;margin:60px auto;" />
    <template v-else>
      <div class="total-bar">共 {{ corpStore.assets.length }} 条记录（本页）</div>
      <n-data-table
        :columns="cols"
        :data="corpStore.assets"
        :bordered="false"
        size="small"
        :row-key="(r: CorporationAsset) => r.item_id"
      />
      <div class="pagination">
        <n-button size="small" :disabled="page <= 1" @click="page--; load()">上一页</n-button>
        <span class="page-num">第 {{ page }} 页</span>
        <n-button size="small" :disabled="corpStore.assets.length < 200" @click="page++; load()">下一页</n-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; margin-bottom: 20px; }
.total-bar { font-size: 0.85rem; color: #87867f; margin-bottom: 12px; }
.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.page-num { font-size: 0.85rem; color: #87867f; }
</style>
