<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '@/stores/admin'
import { useMessage } from 'naive-ui'
import HelmLoader from '@/components/HelmLoader.vue'

const adminStore = useAdminStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)
const backfilling = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    await adminStore.fetchBuckets()
  } finally {
    loading.value = false
  }
  timer = setInterval(() => adminStore.fetchBuckets(), 30_000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })

async function backfill() {
  backfilling.value = true
  try {
    await adminStore.triggerBucketBackfill()
    message.success(t('admin.buckets.backfillSuccess'))
  } catch {
    message.error(t('admin.buckets.backfillFailed'))
  } finally {
    backfilling.value = false
  }
}

function healthColor(health: string) {
  const map: Record<string, string> = {
    available: '#6abf69',
    balanced: '#c96442',
    overload: '#b53333',
    unknown: '#5e5d59',
  }
  return map[health] ?? '#5e5d59'
}
</script>

<template>
  <div>
    <div class="section-header">
      <span class="count-bar">{{ t('admin.buckets.count', { n: adminStore.buckets.length }) }}</span>
      <div style="display:flex;gap:8px">
        <n-button size="small" @click="adminStore.fetchBuckets()">{{ t('common.refresh') }}</n-button>
        <n-button size="small" type="primary" :loading="backfilling" @click="backfill">{{ t('admin.buckets.backfill') }}</n-button>
      </div>
    </div>

    <div v-if="loading" class="helm-section-loader"><HelmLoader :size="48" /></div>

    <div v-if="!loading" class="bucket-grid">
      <div v-for="bucket in adminStore.buckets" :key="bucket.id" class="bucket-card">
        <div class="bucket-top">
          <div>
            <div class="bucket-name">{{ bucket.name }}</div>
            <div class="bucket-desc">{{ bucket.description || '—' }}</div>
          </div>
          <div class="health-dot" :style="{ background: healthColor(bucket.state.health) }" :title="bucket.state.health" />
        </div>
        <div class="bucket-stats">
          <div class="bstat">
            <span class="bstat-label">{{ t('admin.buckets.tokenCount') }}</span>
            <span class="bstat-val">{{ bucket.state.token_count }} / {{ bucket.capacity }}</span>
          </div>
          <div class="bstat">
            <span class="bstat-label">{{ t('admin.buckets.activeTasks') }}</span>
            <span class="bstat-val">{{ bucket.state.active_task_count }}</span>
          </div>
          <div class="bstat">
            <span class="bstat-label">{{ t('common.status') }}</span>
            <span class="bstat-val" :style="{ color: healthColor(bucket.state.health) }">{{ bucket.state.health }}</span>
          </div>
        </div>
        <div class="bucket-footer">
          <span :class="bucket.is_active ? 'tag-active' : 'tag-inactive'">
            {{ bucket.is_active ? t('common.active') : t('common.deactivated') }}
          </span>
          <span class="bucket-meta">
            {{ bucket.state.last_run_at ? new Date(bucket.state.last_run_at).toLocaleString() : t('common.neverRun') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.count-bar { font-size: 0.85rem; color: #87867f; }
.create-form { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; padding: 12px 16px; background: #1e1e1c; border-radius: 6px; }

.bucket-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.bucket-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 16px 18px;
}
.bucket-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.bucket-name { font-size: 0.95rem; font-weight: 500; color: #faf9f5; margin-bottom: 2px; }
.bucket-desc { font-size: 0.78rem; color: #87867f; }
.health-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 3px; }

.bucket-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
.bstat { display: flex; flex-direction: column; gap: 2px; }
.bstat-label { font-size: 0.72rem; color: #5e5d59; }
.bstat-val { font-size: 0.88rem; color: #b0aea5; }

.bucket-footer { display: flex; align-items: center; justify-content: space-between; }
.tag-active { font-size: 0.75rem; color: #6abf69; background: rgba(106,191,105,0.1); padding: 2px 8px; border-radius: 4px; }
.tag-inactive { font-size: 0.75rem; color: #87867f; background: #30302e; padding: 2px 8px; border-radius: 4px; }
.bucket-meta { font-size: 0.75rem; color: #5e5d59; }
</style>
