<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCorporationStore } from '@/stores/corporation'
import { useI18n } from 'vue-i18n'
import type { DataTableColumns } from 'naive-ui'
import type { CorporationMember } from '@/stores/corporation'
import { resolveSdeName } from '@/utils/sde'
import HelmLoader from '@/components/HelmLoader.vue'
import type { SdeName } from '@/utils/sde'

const route = useRoute()
const corpStore = useCorporationStore()
const { t } = useI18n()
const corporationId = Number(route.params.id)
const loading = ref(true)
const search = ref('')

onMounted(async () => {
  try {
    await corpStore.fetchMembers(corporationId)
  } finally {
    loading.value = false
  }
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return corpStore.members
  return corpStore.members.filter(m => String(m.character_id).includes(q))
})

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString()
}

const cols: DataTableColumns<CorporationMember> = [
  { title: 'Character ID', key: 'character_id', width: 120 },
  { title: () => t('corp.joinDate'), key: 'start_date', width: 120, render: r => fmtDate(r.start_date) },
  { title: () => t('corp.lastLogin'), key: 'logon_date', width: 160, render: r => fmtDate(r.logon_date) },
  { title: () => t('corp.lastLogoff'), key: 'logoff_date', width: 160, render: r => fmtDate(r.logoff_date) },
  {
    title: () => t('corp.ship'),
    key: 'ship_type_id',
    ellipsis: true,
    render: r => {
      if (!r.ship_type_id) return '—'
      if (r.ship_type_name && typeof r.ship_type_name === 'object')
        return resolveSdeName(r.ship_type_name as SdeName, String(r.ship_type_id))
      return (r.ship_type_name as string | null) ?? String(r.ship_type_id)
    },
  },
]
</script>

<template>
  <div>
    <div class="header-row">
      <h1 class="page-title h-serif">{{ t('nav.members') }}</h1>
      <n-input
        v-model:value="search"
        :placeholder="t('corp.searchMember')"
        size="small"
        clearable
        style="width:220px"
      />
    </div>

    <div v-if="loading" class="helm-page-loader"><HelmLoader :size="48" /></div>
    <div v-else>
      <div class="total-bar">{{ t('corp.memberTotal', { filtered: filtered.length, total: corpStore.members.length }) }}</div>
      <n-data-table
        :columns="cols"
        :data="filtered"
        :bordered="false"
        size="small"
        :row-key="(r: CorporationMember) => r.character_id"
        :pagination="{ pageSize: 50 }"
      />
    </div>
  </div>
</template>

<style scoped>
.header-row { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 1.6rem; color: #faf9f5; }
.total-bar { font-size: 0.85rem; color: #87867f; margin-bottom: 12px; }
</style>
