<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '@/stores/admin'
import type { DataTableColumns } from 'naive-ui'
import type { AdminUser } from '@/stores/admin'
import { h } from 'vue'
import { NButton, NTag, NSpace, useMessage } from 'naive-ui'

const adminStore = useAdminStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)

const selectedUser = ref<AdminUser | null>(null)
const showRoleModal = ref(false)
const selectedRoleId = ref<number | null>(null)
const submitting = ref(false)

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

function openRoleModal(user: AdminUser) {
  selectedUser.value = user
  selectedRoleId.value = null
  showRoleModal.value = true
}

const availableRoles = computed(() => {
  if (!selectedUser.value) return adminStore.roles
  const currentIds = new Set((selectedUser.value.roles ?? []).map(r => r.id))
  return adminStore.roles.filter(r => !currentIds.has(r.id))
})

async function addRole() {
  if (!selectedUser.value || selectedRoleId.value === null) return
  submitting.value = true
  try {
    await adminStore.assignRole(selectedUser.value.id, selectedRoleId.value)
    const refreshed = adminStore.users.find(u => u.id === selectedUser.value!.id)
    if (refreshed) selectedUser.value = refreshed
    selectedRoleId.value = null
    message.success(t('admin.users.roleAdded'))
  } catch {
    message.error(t('common.operationFailed'))
  } finally {
    submitting.value = false
  }
}

async function removeRole(roleId: number) {
  if (!selectedUser.value) return
  try {
    await adminStore.removeRole(selectedUser.value.id, roleId)
    const refreshed = adminStore.users.find(u => u.id === selectedUser.value!.id)
    if (refreshed) selectedUser.value = refreshed
    message.success(t('admin.users.roleRemoved'))
  } catch {
    message.error(t('common.operationFailed'))
  }
}

const cols: DataTableColumns<AdminUser> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: () => t('admin.users.username'), key: 'username' },
  {
    title: () => t('admin.users.roles'),
    key: 'roles',
    render: r => {
      if (!r.roles?.length) return h('span', { style: 'color:#87867f;font-size:0.78rem' }, '—')
      return h(NSpace, { size: 4 }, {
        default: () => r.roles.map(role =>
          h(NTag, { type: 'default', size: 'small' }, { default: () => role.name })
        ),
      })
    },
  },
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
    title: () => t('common.actions'), key: 'actions', width: 160,
    render: r => h(NSpace, { size: 4 }, {
      default: () => [
        h(NButton, { size: 'tiny', ghost: true, onClick: () => openRoleModal(r) },
          { default: () => t('admin.users.manageRoles') }),
        h(NButton, { size: 'tiny', type: 'error', ghost: true, onClick: () => deactivate(r.id), disabled: !r.is_active },
          { default: () => t('common.deactivate') }),
      ],
    }),
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

    <n-modal v-model:show="showRoleModal" preset="card" :title="t('admin.users.manageRoles')" style="width:480px;max-width:95vw">
      <div v-if="selectedUser">
        <div class="modal-username">{{ selectedUser.username }}</div>

        <div class="modal-section-label">{{ t('admin.users.currentRoles') }}</div>
        <div v-if="!selectedUser.roles?.length" class="empty-hint">{{ t('admin.users.noRoles') }}</div>
        <div v-else class="role-chips">
          <div v-for="role in selectedUser.roles" :key="role.id" class="role-chip">
            <span>{{ role.name }}</span>
            <n-button text size="tiny" type="error" @click="removeRole(role.id)">✕</n-button>
          </div>
        </div>

        <div class="modal-section-label" style="margin-top:16px">{{ t('admin.users.addRole') }}</div>
        <div class="add-role-row">
          <n-select
            v-model:value="selectedRoleId"
            :options="availableRoles.map(r => ({ label: r.name, value: r.id }))"
            :placeholder="t('admin.users.selectRole')"
            size="small"
            style="flex:1"
          />
          <n-button
            size="small"
            type="primary"
            :loading="submitting"
            :disabled="selectedRoleId === null"
            @click="addRole"
          >
            {{ t('common.add') }}
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.count-bar { font-size: 0.85rem; color: #87867f; margin-bottom: 12px; }

.modal-username { font-size: 0.95rem; color: #faf9f5; margin-bottom: 16px; font-weight: 500; }
.modal-section-label { font-size: 0.78rem; color: #87867f; margin-bottom: 8px; }
.empty-hint { font-size: 0.82rem; color: #5e5d59; padding: 6px 0; }

.role-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.role-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #30302e;
  border-radius: 4px;
  font-size: 0.82rem;
  color: #b0aea5;
}

.add-role-row { display: flex; gap: 8px; align-items: center; }
</style>
