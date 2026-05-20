<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useCorporationStore } from '@/stores/corporation'
import { useI18n } from 'vue-i18n'
import type { DataTableColumns } from 'naive-ui'
import type { CorporationAsset } from '@/stores/corporation'
import { resolveSdeName } from '@/utils/sde'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const corpStore = useCorporationStore()
const { t } = useI18n()
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
  {
    title: () => t('common.item'),
    key: 'type_id',
    ellipsis: true,
    render: (r) => {
      const name = resolveSdeName(r.type_name, String(r.type_id))
      if (!r.icon_url) return name
      return h('span', { style: 'display:flex;align-items:center;gap:6px;' }, [
        h('img', { src: r.icon_url, width: 24, height: 24, alt: '', loading: 'lazy', style: 'border-radius:2px;flex-shrink:0;', onError: (e: Event) => { (e.target as HTMLImageElement).style.display = 'none' } }),
        name,
      ])
    },
  },
  { title: 'Location ID', key: 'location_id', width: 120 },
  { title: () => t('common.status'), key: 'location_type', width: 120 },
  { title: () => t('common.quantity'), key: 'quantity', width: 80, align: 'right' },
  {
    title: 'Singleton', key: 'is_singleton', width: 80,
    render: r => r.is_singleton ? 'Singleton' : '—',
  },
]
</script>

<template>
  <div>
    <h1 class="page-title h-serif">{{ t('corp.assets') }}</h1>

    <div v-if="loading" class="helm-page-loader"><HelmLoader :size="48" /></div>
    <template v-else>
      <div class="total-bar">{{ t('corp.assetsCount', { n: corpStore.assets.length }) }}</div>
      <n-data-table
        :columns="cols"
        :data="corpStore.assets"
        :bordered="false"
        size="small"
        :row-key="(r: CorporationAsset) => r.item_id"
      />
      <div class="pagination">
        <n-button size="small" :disabled="page <= 1" @click="page--; load()">{{ t('common.prevPage') }}</n-button>
        <span class="page-num">{{ t('common.page', { n: page }) }}</span>
        <n-button size="small" :disabled="corpStore.assets.length < 200" @click="page++; load()">{{ t('common.nextPage') }}</n-button>
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
