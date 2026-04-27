<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()
const loading = ref(true)

onMounted(async () => {
  try {
    await adminStore.fetchPermissions()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />
    <template v-else>
      <div class="count-bar">{{ adminStore.permissions.length }} 个内置权限</div>
      <div class="perm-table">
        <div class="perm-header perm-row">
          <span>ID</span>
          <span>名称</span>
          <span>作用域类型</span>
        </div>
        <div
          v-for="perm in adminStore.permissions"
          :key="perm.id"
          class="perm-row"
        >
          <span class="perm-id">{{ perm.id }}</span>
          <span class="perm-name">{{ perm.name }}</span>
          <span class="perm-scope">{{ perm.scope_type }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.count-bar { font-size: 0.85rem; color: #87867f; margin-bottom: 12px; }
.perm-table { background: #1e1e1c; border: 1px solid #30302e; border-radius: 8px; overflow: hidden; }
.perm-row {
  display: grid;
  grid-template-columns: 48px 1fr 160px;
  gap: 12px;
  padding: 9px 14px;
  border-bottom: 1px solid #30302e;
  font-size: 0.85rem;
  color: #b0aea5;
}
.perm-row:last-child { border-bottom: none; }
.perm-header { color: #5e5d59; font-size: 0.78rem; }
.perm-id { color: #5e5d59; }
.perm-name { color: #faf9f5; }
.perm-scope {
  font-size: 0.75rem;
  color: #87867f;
  background: #30302e;
  padding: 2px 6px;
  border-radius: 3px;
  height: fit-content;
  align-self: center;
}
</style>
