<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()
const loading = ref(true)

onMounted(async () => {
  try {
    await adminStore.fetchSystemStats()
  } finally {
    loading.value = false
  }
})

const statDefs = [
  { key: 'total_users', label: '用户数' },
  { key: 'total_characters', label: '角色数' },
  { key: 'total_corporations', label: '公司数' },
  { key: 'total_alliances', label: '联盟数' },
  { key: 'total_buckets', label: 'Bucket 数' },
  { key: 'total_bucket_tokens', label: 'Bucket Token 数' },
] as const
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
    <div v-else class="muted">暂无数据</div>
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
