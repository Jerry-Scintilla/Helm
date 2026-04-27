<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '@/stores/character'

const route = useRoute()
const charStore = useCharacterStore()
const characterId = Number(route.params.id)
const loading = ref(true)
const unreadOnly = ref(false)
const filterType = ref<string | null>(null)

onMounted(async () => {
  try {
    await charStore.fetchNotifications(characterId)
  } finally {
    loading.value = false
  }
})

const allTypes = computed(() => {
  const types = new Set(charStore.notifications.map(n => n.type))
  return Array.from(types).sort()
})

const filtered = computed(() => {
  let list = charStore.notifications
  if (unreadOnly.value) list = list.filter(n => !n.is_read)
  if (filterType.value) list = list.filter(n => n.type === filterType.value)
  return list
})

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('zh-CN')
}
</script>

<template>
  <div>
    <div class="header-row">
      <h1 class="page-title h-serif">通知</h1>
      <div class="filters">
        <n-switch v-model:value="unreadOnly" size="small">
          <template #checked>仅未读</template>
          <template #unchecked>全部</template>
        </n-switch>
        <n-select
          v-model:value="filterType"
          :options="[{ label: '全部类型', value: null }, ...allTypes.map(t => ({ label: t, value: t }))]"
          size="small"
          style="width:200px"
          clearable
          placeholder="筛选类型"
        />
      </div>
    </div>

    <n-spin v-if="loading" :size="24" style="display:block;margin:60px auto;" />
    <div v-else-if="filtered.length === 0" class="muted">暂无通知</div>

    <div v-else class="notification-list">
      <div
        v-for="notif in filtered"
        :key="notif.notification_id"
        class="notif-item"
        :class="{ unread: !notif.is_read }"
      >
        <div class="notif-header">
          <span class="notif-type">{{ notif.type }}</span>
          <span class="notif-date">{{ fmtDate(notif.timestamp) }}</span>
          <n-tag v-if="!notif.is_read" size="tiny" type="warning" style="margin-left:8px">未读</n-tag>
        </div>
        <div v-if="notif.text" class="notif-text">{{ notif.text.slice(0, 200) }}{{ notif.text.length > 200 ? '…' : '' }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-row { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 1.6rem; color: #faf9f5; }
.filters { display: flex; align-items: center; gap: 12px; }
.muted { color: #5e5d59; }

.notification-list { display: flex; flex-direction: column; gap: 8px; }
.notif-item {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 12px 16px;
}
.notif-item.unread { border-left: 2px solid #c96442; }
.notif-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.notif-type {
  font-size: 0.82rem;
  font-weight: 500;
  color: #faf9f5;
  background: #30302e;
  padding: 2px 8px;
  border-radius: 4px;
}
.notif-date { font-size: 0.78rem; color: #5e5d59; }
.notif-text { font-size: 0.85rem; color: #87867f; line-height: 1.5; }
</style>
