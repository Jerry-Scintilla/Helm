import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface AdminUser {
  id: number
  username: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

export interface AdminRole {
  id: number
  name: string
  description: string
}

export interface AdminPermission {
  id: number
  name: string
  scope_type: string
}

export interface BucketState {
  token_count: number
  health: 'available' | 'balanced' | 'overload' | 'unknown'
  last_run_at: string | null
  active_task_count: number
}

export interface AdminBucket {
  id: number
  name: string
  capacity: number
  is_active: boolean
  description: string
  created_at: string
  state: BucketState
}

export interface SystemStats {
  total_users: number
  total_characters: number
  total_corporations: number
  total_alliances: number
  total_buckets: number
  total_bucket_tokens: number
}

export const useAdminStore = defineStore('admin', () => {
  const users = ref<AdminUser[]>([])
  const roles = ref<AdminRole[]>([])
  const permissions = ref<AdminPermission[]>([])
  const buckets = ref<AdminBucket[]>([])
  const systemStats = ref<SystemStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchUsers() {
    const res = await api.get('/api/v1/admin/users/')
    users.value = res.data
  }

  async function fetchRoles() {
    const res = await api.get('/api/v1/admin/roles/')
    roles.value = res.data
  }

  async function fetchPermissions() {
    const res = await api.get('/api/v1/admin/permissions/')
    permissions.value = res.data
  }

  async function createRole(name: string, description = '') {
    const res = await api.post('/api/v1/admin/roles/', { name, description })
    await fetchRoles()
    return res.data
  }

  async function deleteRole(roleId: number) {
    await api.delete(`/api/v1/admin/roles/${roleId}`)
    await fetchRoles()
  }

  async function assignRole(userId: number, roleId: number) {
    await api.post(`/api/v1/admin/users/${userId}/roles`, { role_id: roleId })
  }

  async function removeRole(userId: number, roleId: number) {
    await api.delete(`/api/v1/admin/users/${userId}/roles/${roleId}`)
  }

  async function assignPermission(roleId: number, permissionId: number) {
    await api.post(`/api/v1/admin/roles/${roleId}/permissions`, { permission_id: permissionId })
  }

  async function removePermission(roleId: number, permissionId: number) {
    await api.delete(`/api/v1/admin/roles/${roleId}/permissions/${permissionId}`)
  }

  async function deactivateUser(userId: number) {
    await api.delete(`/api/v1/admin/users/${userId}`)
    await fetchUsers()
  }

  async function fetchBuckets() {
    const res = await api.get('/api/v1/admin/buckets/')
    buckets.value = res.data
  }

  async function createBucket(name: string, capacity = 100, description = '') {
    await api.post('/api/v1/admin/buckets/', { name, capacity, description })
    await fetchBuckets()
  }

  async function updateBucket(bucketId: number, data: Partial<{ name: string; capacity: number; is_active: boolean }>) {
    await api.put(`/api/v1/admin/buckets/${bucketId}`, data)
    await fetchBuckets()
  }

  async function fetchSystemStats() {
    const res = await api.get('/api/v1/admin/system/stats')
    systemStats.value = res.data
  }

  return {
    users, roles, permissions, buckets, systemStats, loading, error,
    fetchUsers, fetchRoles, fetchPermissions, createRole, deleteRole,
    assignRole, removeRole, assignPermission, removePermission, deactivateUser,
    fetchBuckets, createBucket, updateBucket, fetchSystemStats,
  }
})
