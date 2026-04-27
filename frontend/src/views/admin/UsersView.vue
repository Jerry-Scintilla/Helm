<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAdminStore } from '@/stores/admin'
import type { DataTableColumns } from 'naive-ui'
import type { AdminUser, AdminRole } from '@/stores/admin'
import { h } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'

const adminStore = useAdminStore()
const message = useMessage()
const loading = ref(true)
const roleModalUser = ref<AdminUser | null>(null)
const selectedRoleId = ref<number | null>(null)

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
    message.success('用户已停用')
  } catch {
    message.error('操作失败')
  }
}

const cols: DataTableColumns<AdminUser> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '用户名', key: 'username' },
  {
    title: '状态', key: 'is_active', width: 80,
    render: r => h(NTag, { type: r.is_active ? 'success' : 'error', size: 'small' }, { default: () => r.is_active ? '活跃' : '停用' }),
  },
  {
    title: '超级用户', key: 'is_superuser', width: 90,
    render: r => r.is_superuser ? h(NTag, { type: 'warning', size: 'small' }, { default: () => 'Super' }) : '—',
  },
  { title: '创建时间', key: 'created_at', width: 140, render: r => new Date(r.created_at).toLocaleDateString('zh-CN') },
  {
    title: '操作', key: 'actions', width: 80,
    render: r => h(NButton, { size: 'tiny', type: 'error', ghost: true, onClick: () => deactivate(r.id), disabled: !r.is_active },
      { default: () => '停用' }),
  },
]
</script>

<template>
  <div>
    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />
    <template v-else>
      <div class="count-bar">{{ adminStore.users.length }} 个用户</div>
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
