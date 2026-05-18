<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '@/stores/admin'
import type { AdminRole } from '@/stores/admin'
import { useMessage } from 'naive-ui'

const adminStore = useAdminStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)
const showCreate = ref(false)
const newRoleName = ref('')
const newRoleDesc = ref('')
const creating = ref(false)

const selectedRole = ref<AdminRole | null>(null)
const showPermModal = ref(false)
const selectedPermId = ref<number | null>(null)
const submitting = ref(false)

onMounted(async () => {
  try {
    await Promise.all([adminStore.fetchRoles(), adminStore.fetchPermissions()])
  } finally {
    loading.value = false
  }
})

async function createRole() {
  if (!newRoleName.value.trim()) return
  creating.value = true
  try {
    await adminStore.createRole(newRoleName.value.trim(), newRoleDesc.value.trim())
    message.success(t('admin.roles.created'))
    showCreate.value = false
    newRoleName.value = ''
    newRoleDesc.value = ''
  } catch {
    message.error(t('common.createFailed'))
  } finally {
    creating.value = false
  }
}

async function deleteRole(id: number) {
  try {
    await adminStore.deleteRole(id)
    message.success(t('admin.roles.deleted'))
  } catch {
    message.error(t('common.deleteFailed'))
  }
}

function openPermModal(role: AdminRole) {
  selectedRole.value = role
  selectedPermId.value = null
  showPermModal.value = true
}

const availablePerms = computed(() => {
  if (!selectedRole.value) return adminStore.permissions
  const currentIds = new Set((selectedRole.value.permissions ?? []).map(p => p.id))
  return adminStore.permissions.filter(p => !currentIds.has(p.id))
})

async function addPermission() {
  if (!selectedRole.value || selectedPermId.value === null) return
  submitting.value = true
  try {
    await adminStore.assignPermission(selectedRole.value.id, selectedPermId.value)
    const refreshed = adminStore.roles.find(r => r.id === selectedRole.value!.id)
    if (refreshed) selectedRole.value = refreshed
    selectedPermId.value = null
    message.success(t('admin.roles.permAdded'))
  } catch {
    message.error(t('common.operationFailed'))
  } finally {
    submitting.value = false
  }
}

async function removePermission(permId: number) {
  if (!selectedRole.value) return
  try {
    await adminStore.removePermission(selectedRole.value.id, permId)
    const refreshed = adminStore.roles.find(r => r.id === selectedRole.value!.id)
    if (refreshed) selectedRole.value = refreshed
    message.success(t('admin.roles.permRemoved'))
  } catch {
    message.error(t('common.operationFailed'))
  }
}
</script>

<template>
  <div>
    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />
    <template v-else>
      <div class="section-header">
        <span class="count-bar">{{ t('admin.roles.count', { n: adminStore.roles.length }) }}</span>
        <n-button size="small" type="primary" @click="showCreate = !showCreate">{{ t('admin.roles.createBtn') }}</n-button>
      </div>

      <n-collapse-transition :show="showCreate">
        <div class="create-form">
          <n-input v-model:value="newRoleName" :placeholder="t('admin.roles.namePlaceholder')" size="small" style="width:200px" />
          <n-input v-model:value="newRoleDesc" :placeholder="t('admin.roles.descPlaceholder')" size="small" style="width:240px" />
          <n-button size="small" type="primary" :loading="creating" @click="createRole">{{ t('common.create') }}</n-button>
          <n-button size="small" @click="showCreate = false">{{ t('common.cancel') }}</n-button>
        </div>
      </n-collapse-transition>

      <div class="role-list">
        <div v-for="role in adminStore.roles" :key="role.id" class="role-card">
          <div class="role-main">
            <div class="role-info">
              <span class="role-name">{{ role.name }}</span>
              <span class="role-desc">{{ role.description }}</span>
            </div>
            <div class="role-perms">
              <span v-if="!role.permissions?.length" class="no-perms">{{ t('admin.roles.noPerms') }}</span>
              <span v-for="perm in role.permissions" :key="perm.id" class="perm-chip">{{ perm.name }}</span>
            </div>
          </div>
          <div class="role-actions">
            <n-button size="tiny" ghost @click="openPermModal(role)">{{ t('admin.roles.managePerms') }}</n-button>
            <n-button size="tiny" type="error" ghost @click="deleteRole(role.id)">{{ t('common.delete') }}</n-button>
          </div>
        </div>
      </div>
    </template>

    <n-modal v-model:show="showPermModal" preset="card" :title="t('admin.roles.managePerms')" style="width:480px;max-width:95vw">
      <div v-if="selectedRole">
        <div class="modal-role-name">{{ selectedRole.name }}</div>

        <div class="modal-section-label">{{ t('admin.roles.currentPerms') }}</div>
        <div v-if="!selectedRole.permissions?.length" class="empty-hint">{{ t('admin.roles.noPerms') }}</div>
        <div v-else class="perm-chips">
          <div v-for="perm in selectedRole.permissions" :key="perm.id" class="perm-item">
            <div class="perm-item-info">
              <span class="perm-item-name">{{ perm.name }}</span>
              <span class="perm-item-scope">{{ perm.scope_type }}</span>
            </div>
            <n-button text size="tiny" type="error" @click="removePermission(perm.id)">✕</n-button>
          </div>
        </div>

        <div class="modal-section-label" style="margin-top:16px">{{ t('admin.roles.addPerm') }}</div>
        <div class="add-row">
          <n-select
            v-model:value="selectedPermId"
            :options="availablePerms.map(p => ({ label: p.name, value: p.id }))"
            :placeholder="t('admin.roles.selectPerm')"
            size="small"
            style="flex:1"
          />
          <n-button size="small" type="primary" :loading="submitting" :disabled="selectedPermId === null" @click="addPermission">
            {{ t('common.add') }}
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.count-bar { font-size: 0.85rem; color: #87867f; }
.create-form { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; padding: 12px 16px; background: #1e1e1c; border-radius: 6px; }

.role-list { display: flex; flex-direction: column; gap: 8px; }
.role-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 6px;
}
.role-main { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 0; }
.role-info { display: flex; flex-direction: column; gap: 2px; }
.role-name { font-size: 0.9rem; color: #faf9f5; }
.role-desc { font-size: 0.78rem; color: #87867f; }
.role-perms { display: flex; flex-wrap: wrap; gap: 4px; }
.no-perms { font-size: 0.75rem; color: #5e5d59; }
.perm-chip {
  font-size: 0.72rem;
  color: #b0aea5;
  background: #30302e;
  padding: 2px 8px;
  border-radius: 3px;
}
.role-actions { display: flex; gap: 6px; flex-shrink: 0; align-self: center; }

/* Modal styles */
.modal-role-name { font-size: 0.95rem; color: #faf9f5; font-weight: 500; margin-bottom: 16px; }
.modal-section-label { font-size: 0.78rem; color: #87867f; margin-bottom: 8px; }
.empty-hint { font-size: 0.82rem; color: #5e5d59; padding: 6px 0; }

.perm-chips { display: flex; flex-direction: column; gap: 4px; }
.perm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #30302e;
  border-radius: 4px;
}
.perm-item-info { display: flex; flex-direction: column; gap: 1px; }
.perm-item-name { font-size: 0.82rem; color: #b0aea5; }
.perm-item-scope { font-size: 0.72rem; color: #5e5d59; }

.add-row { display: flex; gap: 8px; align-items: center; }
</style>
