import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface TaskRun {
  task_id: string
  task_name: string
  queue: string
  status: 'pending' | 'running' | 'success' | 'failure' | 'revoked' | 'retry'
  triggered_by: 'scheduled' | 'manual' | 'system'
  retry_count: number
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  result?: string | null
  error?: string | null
}

export interface TaskListResult {
  total: number
  page: number
  page_size: number
  items: TaskRun[]
}

export interface TaskStats {
  last_24h: {
    success: number
    failure: number
    retry: number
    revoked: number
  }
  currently_active: number
  slowest_tasks: Array<{ task_name: string; avg_duration_seconds: number; count: number }>
}

export interface ScheduledTask {
  name: string
  task: string
  queue: string
  default_seconds: number
  schedule_seconds: number
  is_overridden: boolean
  last_run: {
    task_id: string
    status: string
    completed_at: string | null
    duration_seconds: number | null
  } | null
  estimated_next_run: string | null
}

export interface TaskListFilters {
  status?: string
  task_name?: string
  queue?: string
  triggered_by?: string
  page?: number
  page_size?: number
}

export const useTaskStore = defineStore('tasks', () => {
  const taskList = ref<TaskListResult | null>(null)
  const taskStats = ref<TaskStats | null>(null)
  const scheduledTasks = ref<ScheduledTask[]>([])
  const selectedTask = ref<TaskRun | null>(null)
  const loadingList = ref(false)
  const loadingStats = ref(false)
  const loadingScheduled = ref(false)

  async function fetchTaskList(filters: TaskListFilters = {}) {
    loadingList.value = true
    try {
      const params: Record<string, any> = { page: filters.page ?? 1, page_size: filters.page_size ?? 50 }
      if (filters.status) params.status = filters.status
      if (filters.task_name) params.task_name = filters.task_name
      if (filters.queue) params.queue = filters.queue
      if (filters.triggered_by) params.triggered_by = filters.triggered_by
      const res = await api.get('/api/v1/admin/tasks/', { params })
      taskList.value = res.data
    } finally {
      loadingList.value = false
    }
  }

  async function fetchTaskStats() {
    loadingStats.value = true
    try {
      const res = await api.get('/api/v1/admin/tasks/stats')
      taskStats.value = res.data
    } finally {
      loadingStats.value = false
    }
  }

  async function fetchScheduledTasks() {
    loadingScheduled.value = true
    try {
      const res = await api.get('/api/v1/admin/tasks/scheduled')
      scheduledTasks.value = res.data
    } finally {
      loadingScheduled.value = false
    }
  }

  async function fetchTaskDetail(taskId: string): Promise<TaskRun> {
    const res = await api.get(`/api/v1/admin/tasks/${taskId}`)
    return res.data
  }

  async function triggerScheduledTask(name: string): Promise<{ task_id: string }> {
    const res = await api.post(`/api/v1/admin/tasks/scheduled/${encodeURIComponent(name)}/trigger`)
    return res.data
  }

  async function revokeTask(taskId: string): Promise<void> {
    await api.post(`/api/v1/admin/tasks/${taskId}/revoke`)
  }

  async function updateScheduleInterval(name: string, intervalSeconds: number): Promise<void> {
    await api.put(`/api/v1/admin/tasks/scheduled/${encodeURIComponent(name)}/interval`, {
      interval_seconds: intervalSeconds,
    })
    await fetchScheduledTasks()
  }

  async function resetScheduleInterval(name: string): Promise<void> {
    await api.delete(`/api/v1/admin/tasks/scheduled/${encodeURIComponent(name)}/interval`)
    await fetchScheduledTasks()
  }

  return {
    taskList, taskStats, scheduledTasks, selectedTask,
    loadingList, loadingStats, loadingScheduled,
    fetchTaskList, fetchTaskStats, fetchScheduledTasks,
    fetchTaskDetail, triggerScheduledTask, revokeTask,
    updateScheduleInterval, resetScheduleInterval,
  }
})
