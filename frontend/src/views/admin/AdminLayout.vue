<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { RouterView } from 'vue-router'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const tabs = computed(() => [
  { label: t('admin.tabs.system'), path: '/admin/system' },
  { label: t('admin.tabs.users'), path: '/admin/users' },
  { label: t('admin.tabs.roles'), path: '/admin/roles' },
  { label: t('admin.tabs.sde'), path: '/admin/sde' },
  { label: t('admin.tabs.buckets'), path: '/admin/buckets' },
  { label: t('admin.tabs.tokens'), path: '/admin/tokens' },
  { label: t('admin.tabs.plugins'), path: '/admin/plugins' },
  { label: t('admin.tabs.tasks'), path: '/admin/tasks' },
  { label: t('admin.tabs.market'), path: '/admin/market' },
])

const activeTab = computed(() => route.path)
</script>

<template>
  <div>
    <div class="admin-header">
      <h1 class="admin-title h-serif">{{ t('admin.title') }}</h1>
    </div>
    <div class="admin-tabs">
      <button v-for="tab in tabs" :key="tab.path" class="admin-tab" :class="{ active: activeTab === tab.path }"
        @click="router.push(tab.path)">
        {{ tab.label }}
      </button>
    </div>
    <div class="admin-content">
      <RouterView />
    </div>
  </div>
</template>

<style scoped>
.admin-header {
  margin-bottom: 16px;
}

.admin-title {
  font-size: 1.5rem;
  color: #faf9f5;
}

.admin-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #30302e;
  margin-bottom: 24px;
}

.admin-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 8px 18px;
  font-size: 0.88rem;
  color: #87867f;
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}

.admin-tab:hover {
  color: #b0aea5;
}

.admin-tab.active {
  color: #faf9f5;
  border-bottom-color: #c96442;
}
</style>
