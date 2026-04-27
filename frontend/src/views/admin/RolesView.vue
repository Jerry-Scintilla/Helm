<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { useMessage } from 'naive-ui'

const adminStore = useAdminStore()
const message = useMessage()
const loading = ref(true)
const showCreate = ref(false)
const newRoleName = ref('')
const newRoleDesc = ref('')
const creating = ref(false)

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
    message.success('角色已创建')
    showCreate.value = false
    newRoleName.value = ''
    newRoleDesc.value = ''
  } catch {
    message.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function deleteRole(id: number) {
  try {
    await adminStore.deleteRole(id)
    message.success('角色已删除')
  } catch {
    message.error('删除失败')
  }
}
</script>

<template>
  <div>
    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />
    <template v-else>
      <div class="section-header">
        <span class="count-bar">{{ adminStore.roles.length }} 个角色</span>
        <n-button size="small" type="primary" @click="showCreate = !showCreate">+ 新建角色</n-button>
      </div>

      <n-collapse-transition :show="showCreate">
        <div class="create-form">
          <n-input v-model:value="newRoleName" placeholder="角色名称" size="small" style="width:200px" />
          <n-input v-model:value="newRoleDesc" placeholder="描述（可选）" size="small" style="width:240px" />
          <n-button size="small" type="primary" :loading="creating" @click="createRole">创建</n-button>
          <n-button size="small" @click="showCreate = false">取消</n-button>
        </div>
      </n-collapse-transition>

      <div class="role-list">
        <div v-for="role in adminStore.roles" :key="role.id" class="role-card">
          <div class="role-info">
            <span class="role-name">{{ role.name }}</span>
            <span class="role-desc">{{ role.description }}</span>
          </div>
          <n-button size="tiny" type="error" ghost @click="deleteRole(role.id)">删除</n-button>
        </div>
      </div>

      <!-- Permissions reference -->
      <div class="perm-section">
        <div class="perm-title">内置权限</div>
        <div class="perm-grid">
          <div v-for="perm in adminStore.permissions" :key="perm.id" class="perm-tag">
            {{ perm.name }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.count-bar { font-size: 0.85rem; color: #87867f; }
.create-form { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; padding: 12px 16px; background: #1e1e1c; border-radius: 6px; }

.role-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; }
.role-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 6px;
}
.role-info { display: flex; flex-direction: column; gap: 2px; }
.role-name { font-size: 0.9rem; color: #faf9f5; }
.role-desc { font-size: 0.78rem; color: #87867f; }

.perm-section { border-top: 1px solid #30302e; padding-top: 20px; }
.perm-title { font-size: 0.82rem; color: #87867f; margin-bottom: 10px; }
.perm-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.perm-tag {
  font-size: 0.78rem;
  color: #b0aea5;
  background: #30302e;
  padding: 3px 10px;
  border-radius: 4px;
}
</style>
