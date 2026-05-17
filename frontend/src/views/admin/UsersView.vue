<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '@/stores/admin'
import type { DataTableColumns } from 'naive-ui'
import type { AdminUser } from '@/stores/admin'
import { h } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'

const adminStore = useAdminStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)

onMounted(async () => {
  try {
    await Promise.all([adminStore.fetchUsers(), adminStore.fetchRoles()])
  } finally {
    loading.value = false
  }
})

async function deactivate(userId: number) {
  try {
    await adminStore.deactivateUser(userId)
    message.success(t('admin.users.deactivated'))
  } catch {
    message.error(t('common.operationFailed'))
  }
}

const cols: DataTableColumns<AdminUser> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: () => t('admin.users.username'), key: 'username' },
  {
    title: () => t('common.status'), key: 'is_active', width: 80,
    render: r => h(NTag, { type: r.is_active ? 'success' : 'error', size: 'small' }, { default: () => r.is_active ? t('common.active') : t('common.deactivated') }),
  },
  {
    title: () => t('admin.users.superuser'), key: 'is_superuser', width: 90,
    render: r => r.is_superuser ? h(NTag, { type: 'warning', size: 'small' }, { default: () => 'Super' }) : '—',
  },
  { title: () => t('common.createdAt'), key: 'created_at', width: 140, render: r => new Date(r.created_at).toLocaleDateString() },
  {
    title: () => t('common.actions'), key: 'actions', width: 80,
    render: r => h(NButton, { size: 'tiny', type: 'error', ghost: true, onClick: () => deactivate(r.id), disabled: !r.is_active },
      { default: () => t('common.deactivate') }),
  },
]
</script>

<template>
  <div>
    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />
    <template v-else>
      <div class="count-bar">{{ t('admin.users.count', { n: adminStore.users.length }) }}</div>
      <n-data-table
        :columns="cols"
        :data="adminStore.users"
        :bordered="false"
        size="small"
        :row-key="(r: AdminUser) => r.id"
      />
    </template>
  </div>
</template>

<style scoped>
.count-bar { font-size: 0.85rem; color: #87867f; margin-bottom: 12px; }
</style>
