<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '@/stores/character'
import { useI18n } from 'vue-i18n'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const charStore = useCharacterStore()
const { t, te } = useI18n()

function typeLabel(type: string): string {
  const key = `notif.types.${type}`
  return te(key) ? t(key) : type
}
const characterId = Number(route.params.id)
const loading = ref(true)
const filterType = ref<string | null>(null)
const expandedId = ref<number | null>(null)
const page = ref(1)
const pageSize = 10

async function load() {
  loading.value = true
  expandedId.value = null
  try {
    await charStore.fetchNotifications(characterId, page.value, pageSize, filterType.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(page, load)

function applyFilter() {
  page.value = 1
  load()
}

function toggle(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString()
}
</script>

<template>
  <div>
    <div class="header-row">
      <h1 class="page-title h-serif">{{ t('nav.notifications') }}</h1>
      <div class="filters">
        <n-select
          v-model:value="filterType"
          :options="[
            { label: t('notif.allTypes'), value: null },
            ...Array.from(new Set(charStore.notifications.map(n => n.type))).sort().map(tp => ({ label: typeLabel(tp), value: tp }))
          ]"
          size="small"
          style="width:220px"
          clearable
          :placeholder="t('notif.filterType')"
          @update:value="applyFilter"
        />
      </div>
    </div>

    <div v-if="loading" class="helm-page-loader"><HelmLoader :size="48" /></div>
    <div v-else-if="charStore.notifications.length === 0" class="muted">{{ t('notif.empty') }}</div>

    <div v-else class="notification-list">
      <div
        v-for="notif in charStore.notifications"
        :key="notif.notification_id"
        class="notif-item"
        :class="{ expanded: expandedId === notif.notification_id }"
      >
        <!-- Header row — always visible, click to expand -->
        <div class="notif-header" @click="toggle(notif.notification_id)">
          <span class="notif-type" :title="notif.type">{{ typeLabel(notif.type) }}</span>
          <span v-if="notif.sender_name" class="notif-sender">{{ notif.sender_name }}</span>
          <span class="notif-date">{{ fmtDate(notif.timestamp) }}</span>
          <span class="notif-arrow" :class="{ open: expandedId === notif.notification_id }">›</span>
        </div>

        <!-- Expanded body -->
        <div v-if="expandedId === notif.notification_id" class="notif-body-wrap">
          <div
            v-if="notif.rendered_text"
            class="notif-rendered"
            v-html="notif.rendered_text"
          />
          <div v-else class="notif-raw">{{ notif.text }}</div>
        </div>
      </div>
    </div>

    <div v-if="charStore.notificationTotal > pageSize" class="pagination-bar">
      <n-pagination
        v-model:page="page"
        :page-count="Math.ceil(charStore.notificationTotal / pageSize)"
        :page-slot="5"
        show-quick-jumper
      />
    </div>
  </div>
</template>

<style scoped>
.header-row { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 1.6rem; color: #faf9f5; }
.filters { display: flex; align-items: center; gap: 12px; }
.muted { color: #5e5d59; }

.notification-list { display: flex; flex-direction: column; gap: 6px; }

.notif-item {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.15s;
}
.notif-item.expanded { border-color: #3d3d3a; }

.notif-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  flex-wrap: wrap;
  user-select: none;
}
.notif-header:hover { background: rgba(255,255,255,0.02); }

.notif-type {
  font-size: 0.82rem;
  font-weight: 500;
  color: #faf9f5;
  background: #30302e;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}
.notif-sender { font-size: 0.82rem; color: #d97757; }
.notif-date { font-size: 0.78rem; color: #5e5d59; }
.notif-arrow {
  margin-left: auto;
  font-size: 1rem;
  color: #5e5d59;
  display: inline-block;
  transition: transform 0.15s ease;
  flex-shrink: 0;
}
.notif-arrow.open { transform: rotate(90deg); }

/* Expanded body */
.notif-body-wrap {
  border-top: 1px solid #2a2a28;
  padding: 12px 16px;
}
.notif-raw {
  font-size: 0.83rem;
  color: #87867f;
  white-space: pre-wrap;
  font-family: monospace;
}

/* Rendered notification HTML (from backend) */
.notif-rendered :deep(.notif-body) {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.notif-rendered :deep(.nf-row) {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 8px;
  align-items: baseline;
  padding: 2px 0;
}
.notif-rendered :deep(.nf-item) {
  padding: 2px 0 2px 188px;
}
.notif-rendered :deep(.nf-cont) {
  font-size: 0.82rem;
  color: #5e5d59;
  padding: 1px 0;
}
.notif-rendered :deep(.nf-key) {
  font-size: 0.78rem;
  color: #5e5d59;
  font-family: ui-monospace, monospace;
  text-align: right;
  padding-right: 4px;
  white-space: nowrap;
}
.notif-rendered :deep(.nf-val) {
  font-size: 0.85rem;
  color: #b0aea5;
  word-break: break-word;
}
.notif-rendered :deep(.nf-val b) { color: #faf9f5; font-weight: 500; }
.notif-rendered :deep(.nf-name) {
  color: #d97757;
  font-weight: 500;
}
.notif-rendered :deep(.nf-id) {
  font-size: 0.75rem;
  color: #5e5d59;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  padding: 16px 0 8px;
}
</style>
