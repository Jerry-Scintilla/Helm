<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTaskStore, type TaskRun, type TaskListFilters } from '@/stores/tasks'
import { useMessage } from 'naive-ui'

const taskStore = useTaskStore()
const message = useMessage()

// Sub-tab: 'history' | 'scheduled'
const activeTab = ref<'history' | 'scheduled'>('history')

// Filters for task history
const filterStatus = ref('')
const filterQueue = ref('')
const filterTaskName = ref('')
const filterTriggeredBy = ref('')
const currentPage = ref(1)

// Detail drawer
const drawerVisible = ref(false)
const drawerTask = ref<TaskRun | null>(null)
const drawerLoading = ref(false)

// Triggering
const triggeringMap = ref<Record<string, boolean>>({})
// Revoking
const revokingMap = ref<Record<string, boolean>>({})

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await Promise.all([taskStore.fetchTaskStats(), loadHistory(), taskStore.fetchScheduledTasks()])
  pollTimer = setInterval(async () => {
    await Promise.all([taskStore.fetchTaskStats(), loadHistory(), taskStore.fetchScheduledTasks()])
  }, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function loadHistory() {
  const filters: TaskListFilters = {
    page: currentPage.value,
    page_size: 50,
  }
  if (filterStatus.value) filters.status = filterStatus.value
  if (filterQueue.value) filters.queue = filterQueue.value
  if (filterTaskName.value) filters.task_name = filterTaskName.value
  if (filterTriggeredBy.value) filters.triggered_by = filterTriggeredBy.value
  await taskStore.fetchTaskList(filters)
}

async function applyFilters() {
  currentPage.value = 1
  await loadHistory()
}

async function clearFilters() {
  filterStatus.value = ''
  filterQueue.value = ''
  filterTaskName.value = ''
  filterTriggeredBy.value = ''
  currentPage.value = 1
  await loadHistory()
}

async function onPageChange(page: number) {
  currentPage.value = page
  await loadHistory()
}

async function openDetail(task: TaskRun) {
  drawerVisible.value = true
  drawerLoading.value = true
  try {
    drawerTask.value = await taskStore.fetchTaskDetail(task.task_id)
  } catch {
    drawerTask.value = task
  } finally {
    drawerLoading.value = false
  }
}

async function triggerScheduled(name: string) {
  triggeringMap.value[name] = true
  try {
    const r = await taskStore.triggerScheduledTask(name)
    message.success(`已触发，任务 ID: ${r.task_id.slice(0, 8)}…`)
    await Promise.all([loadHistory(), taskStore.fetchScheduledTasks()])
  } catch (e: any) {
    message.error(e.response?.data?.detail ?? '触发失败')
  } finally {
    triggeringMap.value[name] = false
  }
}

async function revokeTask(taskId: string) {
  revokingMap.value[taskId] = true
  try {
    await taskStore.revokeTask(taskId)
    message.success('撤销指令已发送')
    await loadHistory()
  } catch (e: any) {
    message.error(e.response?.data?.detail ?? '撤销失败')
  } finally {
    revokingMap.value[taskId] = false
  }
}

// ── Computed helpers ──────────────────────────────────────────────────────────

const stats = computed(() => taskStore.taskStats)

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'running', label: '运行中' },
  { value: 'pending', label: '等待中' },
  { value: 'success', label: '成功' },
  { value: 'failure', label: '失败' },
  { value: 'retry', label: '重试中' },
  { value: 'revoked', label: '已撤销' },
]

const triggerByOptions = [
  { value: '', label: '全部来源' },
  { value: 'scheduled', label: '定时' },
  { value: 'manual', label: '手动' },
  { value: 'system', label: '系统' },
]

const queueOptions = computed(() => {
  const queues = new Set<string>()
  taskStore.taskList?.items.forEach(t => queues.add(t.queue))
  return [{ value: '', label: '全部队列' }, ...[...queues].map(q => ({ value: q, label: q }))]
})

function shortName(fullName: string): string {
  const parts = fullName.split('.')
  return parts.slice(-2).join('.')
}

function formatDuration(s: number | null): string {
  if (s === null) return '—'
  if (s < 1) return `${Math.round(s * 1000)}ms`
  if (s < 60) return `${s.toFixed(1)}s`
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

function formatSchedule(seconds: number): string {
  if (seconds >= 86400) return `每 ${Math.round(seconds / 86400)} 天`
  if (seconds >= 3600) return `每 ${Math.round(seconds / 3600)} 小时`
  if (seconds >= 60) return `每 ${Math.round(seconds / 60)} 分钟`
  return `每 ${seconds} 秒`
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function statusColor(status: string): string {
  const map: Record<string, string> = {
    success: '#6abf69',
    failure: '#b53333',
    running: '#c96442',
    pending: '#87867f',
    retry: '#d97757',
    revoked: '#5e5d59',
  }
  return map[status] ?? '#87867f'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    success: '成功',
    failure: '失败',
    running: '运行中',
    pending: '等待中',
    retry: '重试中',
    revoked: '已撤销',
  }
  return map[status] ?? status
}

function triggerByLabel(v: string): string {
  const map: Record<string, string> = { scheduled: '定时', manual: '手动', system: '系统' }
  return map[v] ?? v
}
</script>

<template>
  <div class="tasks-root">
    <!-- Stats cards -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">当前活跃</div>
        <div class="stat-value" style="color: #c96442">{{ stats?.currently_active ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">24h 成功</div>
        <div class="stat-value" style="color: #6abf69">{{ stats?.last_24h.success ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">24h 失败</div>
        <div class="stat-value" style="color: #b53333">{{ stats?.last_24h.failure ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">24h 重试</div>
        <div class="stat-value" style="color: #d97757">{{ stats?.last_24h.retry ?? '—' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">24h 撤销</div>
        <div class="stat-value" style="color: #5e5d59">{{ stats?.last_24h.revoked ?? '—' }}</div>
      </div>
    </div>

    <!-- Slowest tasks summary (if any) -->
    <div v-if="stats?.slowest_tasks?.length" class="slowest-row">
      <span class="slowest-label">最慢任务 (24h)：</span>
      <span v-for="t in stats.slowest_tasks.slice(0, 3)" :key="t.task_name" class="slowest-chip">
        {{ shortName(t.task_name) }} <span class="slowest-dur">{{ formatDuration(t.avg_duration_seconds) }}</span>
      </span>
    </div>

    <!-- Sub-tabs -->
    <div class="sub-tabs">
      <button class="sub-tab" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
        任务历史
      </button>
      <button class="sub-tab" :class="{ active: activeTab === 'scheduled' }" @click="activeTab = 'scheduled'">
        定时任务 <span class="sub-tab-count">{{ taskStore.scheduledTasks.length }}</span>
      </button>
    </div>

    <!-- ── HISTORY TAB ─────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'history'">
      <!-- Filters -->
      <div class="filter-row">
        <select v-model="filterStatus" class="filter-select" @change="applyFilters">
          <option v-for="o in statusOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <select v-model="filterQueue" class="filter-select" @change="applyFilters">
          <option v-for="o in queueOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <select v-model="filterTriggeredBy" class="filter-select" @change="applyFilters">
          <option v-for="o in triggerByOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <input
          v-model="filterTaskName"
          class="filter-input"
          placeholder="搜索任务名…"
          @keydown.enter="applyFilters"
        />
        <button class="btn-secondary" @click="applyFilters">筛选</button>
        <button class="btn-ghost" @click="clearFilters">清除</button>
        <span class="total-count" v-if="taskStore.taskList">共 {{ taskStore.taskList.total }} 条</span>
      </div>

      <!-- Table -->
      <div class="table-wrap">
        <n-spin v-if="taskStore.loadingList && !taskStore.taskList" :size="20" style="display:block;margin:40px auto;" />
        <table v-else class="task-table">
          <thead>
            <tr>
              <th>任务名</th>
              <th>队列</th>
              <th>状态</th>
              <th>来源</th>
              <th>重试</th>
              <th>开始时间</th>
              <th>耗时</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in taskStore.taskList?.items ?? []"
              :key="task.task_id"
              class="task-row"
              @click="openDetail(task)"
            >
              <td class="task-name-cell">
                <span class="task-short">{{ shortName(task.task_name) }}</span>
                <span class="task-full">{{ task.task_name }}</span>
              </td>
              <td><span class="queue-badge">{{ task.queue }}</span></td>
              <td>
                <span class="status-badge" :style="{ color: statusColor(task.status), borderColor: statusColor(task.status) }">
                  {{ statusLabel(task.status) }}
                </span>
              </td>
              <td class="muted-cell">{{ triggerByLabel(task.triggered_by) }}</td>
              <td class="muted-cell">{{ task.retry_count > 0 ? task.retry_count : '—' }}</td>
              <td class="muted-cell time-cell">{{ formatTime(task.started_at) }}</td>
              <td class="muted-cell">{{ formatDuration(task.duration_seconds) }}</td>
              <td @click.stop>
                <button
                  v-if="task.status === 'running' || task.status === 'pending'"
                  class="btn-danger-sm"
                  :disabled="!!revokingMap[task.task_id]"
                  @click="revokeTask(task.task_id)"
                >
                  {{ revokingMap[task.task_id] ? '…' : '撤销' }}
                </button>
              </td>
            </tr>
            <tr v-if="!taskStore.taskList?.items?.length">
              <td colspan="8" class="empty-cell">暂无任务记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="taskStore.taskList && taskStore.taskList.total > 50" class="pagination">
        <button
          class="page-btn"
          :disabled="currentPage <= 1"
          @click="onPageChange(currentPage - 1)"
        >上一页</button>
        <span class="page-info">
          第 {{ currentPage }} 页 / 共 {{ Math.ceil(taskStore.taskList.total / 50) }} 页
        </span>
        <button
          class="page-btn"
          :disabled="currentPage >= Math.ceil(taskStore.taskList.total / 50)"
          @click="onPageChange(currentPage + 1)"
        >下一页</button>
      </div>
    </div>

    <!-- ── SCHEDULED TAB ──────────────────────────────────────────────── -->
    <div v-if="activeTab === 'scheduled'">
      <div class="table-wrap">
        <n-spin v-if="taskStore.loadingScheduled && !taskStore.scheduledTasks.length" :size="20" style="display:block;margin:40px auto;" />
        <table v-else class="task-table">
          <thead>
            <tr>
              <th>计划名</th>
              <th>任务</th>
              <th>队列</th>
              <th>周期</th>
              <th>上次状态</th>
              <th>上次完成</th>
              <th>下次预计</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in taskStore.scheduledTasks" :key="s.name" class="task-row">
              <td class="task-name-cell">
                <span class="task-short">{{ s.name }}</span>
              </td>
              <td>
                <span class="task-full-only">{{ shortName(s.task) }}</span>
              </td>
              <td><span class="queue-badge">{{ s.queue }}</span></td>
              <td class="muted-cell">{{ formatSchedule(s.schedule_seconds) }}</td>
              <td>
                <span v-if="s.last_run" class="status-badge"
                  :style="{ color: statusColor(s.last_run.status), borderColor: statusColor(s.last_run.status) }">
                  {{ statusLabel(s.last_run.status) }}
                </span>
                <span v-else class="muted-cell">从未运行</span>
              </td>
              <td class="muted-cell time-cell">{{ formatTime(s.last_run?.completed_at ?? null) }}</td>
              <td class="muted-cell time-cell">{{ formatTime(s.estimated_next_run) }}</td>
              <td>
                <button
                  class="btn-trigger"
                  :disabled="!!triggeringMap[s.name]"
                  @click="triggerScheduled(s.name)"
                >
                  {{ triggeringMap[s.name] ? '触发中…' : '立即执行' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── DETAIL DRAWER ───────────────────────────────────────────────── -->
    <div v-if="drawerVisible" class="drawer-overlay" @click.self="drawerVisible = false">
      <div class="drawer">
        <div class="drawer-header">
          <span class="drawer-title h-serif">任务详情</span>
          <button class="drawer-close" @click="drawerVisible = false">✕</button>
        </div>
        <div class="drawer-body">
          <n-spin v-if="drawerLoading" :size="20" style="display:block;margin:40px auto;" />
          <template v-else-if="drawerTask">
            <div class="detail-grid">
              <div class="detail-item">
                <div class="detail-label">任务 ID</div>
                <div class="detail-value mono">{{ drawerTask.task_id }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">任务名</div>
                <div class="detail-value mono">{{ drawerTask.task_name }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">状态</div>
                <div class="detail-value">
                  <span class="status-badge"
                    :style="{ color: statusColor(drawerTask.status), borderColor: statusColor(drawerTask.status) }">
                    {{ statusLabel(drawerTask.status) }}
                  </span>
                </div>
              </div>
              <div class="detail-item">
                <div class="detail-label">队列</div>
                <div class="detail-value"><span class="queue-badge">{{ drawerTask.queue }}</span></div>
              </div>
              <div class="detail-item">
                <div class="detail-label">触发来源</div>
                <div class="detail-value">{{ triggerByLabel(drawerTask.triggered_by) }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">重试次数</div>
                <div class="detail-value">{{ drawerTask.retry_count }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">创建时间</div>
                <div class="detail-value">{{ formatTime(drawerTask.created_at) }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">开始时间</div>
                <div class="detail-value">{{ formatTime(drawerTask.started_at) }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">完成时间</div>
                <div class="detail-value">{{ formatTime(drawerTask.completed_at) }}</div>
              </div>
              <div class="detail-item">
                <div class="detail-label">耗时</div>
                <div class="detail-value">{{ formatDuration(drawerTask.duration_seconds) }}</div>
              </div>
            </div>

            <div v-if="drawerTask.result" class="detail-block">
              <div class="detail-block-label">执行结果</div>
              <pre class="code-block">{{ drawerTask.result }}</pre>
            </div>

            <div v-if="drawerTask.error" class="detail-block">
              <div class="detail-block-label" style="color: #b53333">错误信息</div>
              <pre class="code-block error-pre">{{ drawerTask.error }}</pre>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tasks-root { position: relative; }

/* Stats */
.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.stat-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 14px 20px;
  min-width: 110px;
}
.stat-label { font-size: 0.75rem; color: #5e5d59; margin-bottom: 6px; }
.stat-value { font-size: 1.6rem; font-weight: 500; font-family: Georgia, serif; color: #faf9f5; }

/* Slowest */
.slowest-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.slowest-label { font-size: 0.75rem; color: #5e5d59; }
.slowest-chip {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 0.75rem;
  color: #87867f;
  display: flex;
  gap: 6px;
  align-items: center;
}
.slowest-dur { color: #d97757; }

/* Sub-tabs */
.sub-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #30302e;
  margin-bottom: 16px;
}
.sub-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 7px 16px;
  font-size: 0.85rem;
  color: #87867f;
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.sub-tab:hover { color: #b0aea5; }
.sub-tab.active { color: #faf9f5; border-bottom-color: #c96442; }
.sub-tab-count {
  background: #30302e;
  border-radius: 10px;
  padding: 1px 7px;
  font-size: 0.7rem;
  color: #87867f;
}

/* Filters */
.filter-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-select, .filter-input {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 6px;
  color: #b0aea5;
  font-size: 0.82rem;
  padding: 5px 10px;
  outline: none;
  transition: border-color 0.15s;
}
.filter-select:focus, .filter-input:focus { border-color: #5e5d59; }
.filter-input { min-width: 160px; }
.total-count { font-size: 0.78rem; color: #5e5d59; margin-left: auto; }

/* Buttons */
.btn-secondary {
  background: #30302e;
  border: none;
  border-radius: 6px;
  color: #b0aea5;
  font-size: 0.82rem;
  padding: 5px 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-secondary:hover { background: #3d3d3a; }
.btn-ghost {
  background: none;
  border: 1px solid #30302e;
  border-radius: 6px;
  color: #5e5d59;
  font-size: 0.82rem;
  padding: 5px 12px;
  cursor: pointer;
  transition: color 0.15s;
}
.btn-ghost:hover { color: #87867f; }
.btn-danger-sm {
  background: rgba(181, 51, 51, 0.15);
  border: 1px solid #b53333;
  border-radius: 5px;
  color: #b53333;
  font-size: 0.75rem;
  padding: 2px 8px;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.btn-danger-sm:hover:not(:disabled) { background: rgba(181, 51, 51, 0.25); }
.btn-danger-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-trigger {
  background: #c96442;
  border: none;
  border-radius: 6px;
  color: #faf9f5;
  font-size: 0.78rem;
  padding: 4px 12px;
  cursor: pointer;
  transition: opacity 0.15s;
  white-space: nowrap;
  box-shadow: #c96442 0px 0px 0px 0px, #c96442 0px 0px 0px 1px;
}
.btn-trigger:hover:not(:disabled) { opacity: 0.85; }
.btn-trigger:disabled { opacity: 0.45; cursor: not-allowed; }

/* Table */
.table-wrap { overflow-x: auto; }
.task-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.task-table th {
  text-align: left;
  padding: 8px 12px;
  color: #5e5d59;
  font-size: 0.72rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #30302e;
  white-space: nowrap;
}
.task-row {
  cursor: pointer;
  transition: background 0.1s;
}
.task-row:hover { background: rgba(255, 255, 255, 0.03); }
.task-row td {
  padding: 9px 12px;
  border-bottom: 1px solid #252523;
  vertical-align: middle;
}
.task-name-cell { max-width: 220px; }
.task-short { display: block; color: #b0aea5; font-size: 0.82rem; }
.task-full { display: block; color: #5e5d59; font-size: 0.7rem; font-family: monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 210px; }
.task-full-only { color: #87867f; font-size: 0.78rem; font-family: monospace; }
.muted-cell { color: #5e5d59; }
.time-cell { white-space: nowrap; font-size: 0.78rem; }
.empty-cell { text-align: center; padding: 40px; color: #5e5d59; }

.status-badge {
  display: inline-block;
  border: 1px solid;
  border-radius: 4px;
  padding: 1px 7px;
  font-size: 0.72rem;
  white-space: nowrap;
}
.queue-badge {
  display: inline-block;
  background: #252523;
  border: 1px solid #30302e;
  border-radius: 4px;
  padding: 1px 7px;
  font-size: 0.72rem;
  color: #87867f;
  white-space: nowrap;
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  justify-content: flex-end;
}
.page-btn {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 6px;
  color: #b0aea5;
  font-size: 0.82rem;
  padding: 5px 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.page-btn:hover:not(:disabled) { background: #30302e; }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 0.78rem; color: #5e5d59; }

/* Drawer */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 200;
  display: flex;
  justify-content: flex-end;
}
.drawer {
  width: min(540px, 100vw);
  height: 100vh;
  background: #141413;
  border-left: 1px solid #30302e;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #30302e;
  flex-shrink: 0;
}
.drawer-title {
  font-size: 1.05rem;
  color: #faf9f5;
  font-family: Georgia, serif;
}
.drawer-close {
  background: none;
  border: none;
  color: #5e5d59;
  font-size: 1rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: color 0.15s;
}
.drawer-close:hover { color: #b0aea5; }
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}
.detail-item {}
.detail-label { font-size: 0.72rem; color: #5e5d59; margin-bottom: 4px; letter-spacing: 0.04em; }
.detail-value { font-size: 0.88rem; color: #b0aea5; }
.detail-value.mono { font-family: monospace; font-size: 0.78rem; word-break: break-all; }

.detail-block { margin-bottom: 16px; }
.detail-block-label { font-size: 0.75rem; color: #5e5d59; margin-bottom: 8px; letter-spacing: 0.04em; }
.code-block {
  background: #1a1a18;
  border: 1px solid #30302e;
  border-radius: 6px;
  padding: 12px 14px;
  font-family: monospace;
  font-size: 0.75rem;
  color: #87867f;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 320px;
  overflow-y: auto;
  line-height: 1.55;
}
.error-pre { color: #c97575; }

.h-serif { font-family: Georgia, serif; }
</style>
