<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { RouterView } from 'vue-router'
import { computed } from 'vue'

const router = useRouter()
const route = useRoute()

const tabs = [
  { label: '系统', path: '/admin/system' },
  { label: '用户', path: '/admin/users' },
  { label: '角色权限', path: '/admin/roles' },
  { label: 'SDE', path: '/admin/sde' },
  { label: 'Buckets', path: '/admin/buckets' },
  { label: 'API Token', path: '/admin/tokens' },
]

const activeTab = computed(() => route.path)
</script>

<template>
  <div>
    <div class="admin-header">
      <h1 class="admin-title h-serif">管理后台</h1>
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
