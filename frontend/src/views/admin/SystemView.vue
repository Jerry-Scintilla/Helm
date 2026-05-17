<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()
const { t } = useI18n()
const loading = ref(true)

onMounted(async () => {
  try {
    await adminStore.fetchSystemStats()
  } finally {
    loading.value = false
  }
})

const statDefs = computed(() => [
  { key: 'total_users', label: t('admin.stat.users') },
  { key: 'total_characters', label: t('admin.stat.characters') },
  { key: 'total_corporations', label: t('admin.stat.corporations') },
  { key: 'total_alliances', label: t('admin.stat.alliances') },
  { key: 'total_buckets', label: t('admin.stat.buckets') },
  { key: 'total_bucket_tokens', label: t('admin.stat.bucketTokens') },
] as const)
</script>

<template>
  <div>
    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />
    <div v-else-if="adminStore.systemStats" class="stats-grid">
      <div v-for="def in statDefs" :key="def.key" class="stat-card">
        <div class="stat-label">{{ def.label }}</div>
        <div class="stat-value">{{ adminStore.systemStats[def.key] }}</div>
      </div>
    </div>
    <div v-else class="muted">{{ t('common.noData') }}</div>
  </div>
</template>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.stat-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 20px 20px;
}
.stat-label { font-size: 0.8rem; color: #87867f; margin-bottom: 10px; }
.stat-value {
  font-size: 2rem;
  font-weight: 500;
  color: #faf9f5;
  font-family: Georgia, serif;
  line-height: 1;
}
.muted { color: #5e5d59; }
</style>
