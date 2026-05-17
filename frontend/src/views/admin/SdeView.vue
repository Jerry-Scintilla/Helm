<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '@/stores/admin'
import { useMessage } from 'naive-ui'

const adminStore = useAdminStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)
const importing = ref(false)
const uploading = ref(false)
const customUrlEnabled = ref(false)
const customUrl = ref('')
const uploadFile = ref<File | null>(null)

const DEFAULT_URL = 'https://developers.eveonline.com/static-data/eve-online-static-data-latest-jsonl.zip'

onMounted(async () => {
  try {
    await adminStore.fetchSdeStatus()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  adminStore.stopImportPolling()
})

async function handleImport() {
  importing.value = true
  try {
    const url = customUrlEnabled.value ? customUrl.value : undefined
    const taskId = await adminStore.triggerSdeImport(url)
    message.info(t('admin.sde.importStarted'))
    adminStore.startImportPolling(taskId, (task) => {
      if (task.status === 'success') {
        message.success(t('admin.sde.importSuccess'))
      } else {
        message.error(t('admin.sde.importFailed'))
      }
    })
  } catch (e: any) {
    message.error(e.response?.data?.detail ?? t('admin.sde.importStartFailed'))
  } finally {
    importing.value = false
  }
}

async function handleUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  try {
    const taskId = await adminStore.triggerSdeUpload(uploadFile.value)
    message.info(t('admin.sde.uploadStarted'))
    adminStore.startImportPolling(taskId, (task) => {
      if (task.status === 'success') {
        message.success(t('admin.sde.importSuccess'))
      } else {
        message.error(t('admin.sde.importFailed'))
      }
    })
    uploadFile.value = null
  } catch (e: any) {
    message.error(e.response?.data?.detail ?? t('admin.sde.uploadFailed'))
  } finally {
    uploading.value = false
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    uploadFile.value = input.files[0] ?? null
  }
}

const statusColor = computed(() => {
  const map: Record<string, string> = {
    idle: '#87867f',
    running: '#c96442',
    success: '#6abf69',
    failed: '#b53333',
  }
  return map[adminStore.sdeStatus?.status ?? 'idle'] ?? '#87867f'
})

const statusLabel = computed(() => {
  const key = adminStore.sdeStatus?.status ?? 'idle'
  return t(`admin.sde.statusMap.${key}` as any) ?? key
})

const taskStatusLabel = computed(() => {
  if (!adminStore.currentTask) return null
  const key = adminStore.currentTask.status
  return t(`admin.sde.taskStatusMap.${key}` as any) ?? key
})

const isRunning = computed(() => adminStore.sdeStatus?.status === 'running')
</script>

<template>
  <div>
    <div class="section-header">
      <span class="count-bar">{{ t('admin.sde.statusTitle') }}</span>
      <n-button size="small" @click="adminStore.fetchSdeStatus()">{{ t('common.refresh') }}</n-button>
    </div>

    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />

    <template v-else-if="adminStore.sdeStatus">
      <div class="sde-grid">
        <div class="sde-card">
          <div class="card-label">{{ t('admin.sde.currentStatus') }}</div>
          <div class="card-value" :style="{ color: statusColor }">{{ statusLabel }}</div>
          <div v-if="adminStore.currentTask && isRunning" class="task-status">
            {{ t('admin.sde.task') }} {{ taskStatusLabel }}
          </div>
        </div>

        <div class="sde-card">
          <div class="card-label">{{ t('common.version') }}</div>
          <div class="card-value">{{ adminStore.sdeStatus.version ?? '—' }}</div>
        </div>

        <div class="sde-card">
          <div class="card-label">{{ t('admin.sde.releaseDate') }}</div>
          <div class="card-value small">
            {{ adminStore.sdeStatus.release_date
                ? new Date(adminStore.sdeStatus.release_date).toLocaleDateString()
                : '—' }}
          </div>
        </div>

        <div class="sde-card">
          <div class="card-label">{{ t('admin.sde.typeCount') }}</div>
          <div class="card-value">{{ adminStore.sdeStatus.row_count?.toLocaleString() ?? '—' }}</div>
        </div>

        <div class="sde-card">
          <div class="card-label">{{ t('admin.sde.lastImport') }}</div>
          <div class="card-value small">
            {{ adminStore.sdeStatus.last_import_at
                ? new Date(adminStore.sdeStatus.last_import_at).toLocaleString()
                : t('common.neverRun') }}
          </div>
        </div>
      </div>

      <div v-if="adminStore.sdeStatus.source_url" class="source-url">
        {{ t('admin.sde.source') }}: <code>{{ adminStore.sdeStatus.source_url }}</code>
      </div>

      <div v-if="adminStore.sdeStatus.last_error" class="error-box">
        <strong>{{ t('admin.sde.errorLabel') }}</strong> {{ adminStore.sdeStatus.last_error }}
      </div>

      <!-- Import result -->
      <div v-if="adminStore.currentTask?.result" class="result-box">
        <div class="result-title">{{ t('admin.sde.importDetails') }}</div>
        <div class="result-grid">
          <div class="result-item">
            <span class="result-label">{{ t('admin.sde.types') }}</span>
            <span class="result-value">{{ adminStore.currentTask.result.type_count?.toLocaleString() ?? '—' }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">{{ t('admin.sde.groups') }}</span>
            <span class="result-value">{{ adminStore.currentTask.result.group_count?.toLocaleString() ?? '—' }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">{{ t('admin.sde.categories') }}</span>
            <span class="result-value">{{ adminStore.currentTask.result.category_count?.toLocaleString() ?? '—' }}</span>
          </div>
        </div>
      </div>

      <div class="import-cards">
        <!-- URL import -->
        <div class="import-card">
          <div class="import-card-header">
            <span class="import-card-icon">🔗</span>
            <span class="import-card-title">{{ t('admin.sde.importFromUrl') }}</span>
          </div>
          <div class="import-card-body">
            <div class="url-display-row">
              <span class="url-label">{{ t('admin.sde.defaultSource') }}</span>
              <code class="url-code">{{ DEFAULT_URL }}</code>
            </div>
            <div class="import-row">
              <n-checkbox v-model:checked="customUrlEnabled" class="import-checkbox">
                {{ t('admin.sde.customUrl') }}
              </n-checkbox>
              <n-input
                v-if="customUrlEnabled"
                v-model:value="customUrl"
                placeholder="https://..."
                size="small"
                class="custom-url-input"
              />
            </div>
            <div class="import-action">
              <n-button
                :loading="importing || isRunning"
                :disabled="isRunning"
                class="action-btn"
                @click="handleImport"
              >
                {{ isRunning ? t('admin.sde.importing') : t('admin.sde.startImport') }}
              </n-button>
            </div>
          </div>
        </div>

        <!-- File upload -->
        <div class="import-card">
          <div class="import-card-header">
            <span class="import-card-icon">📦</span>
            <span class="import-card-title">{{ t('admin.sde.uploadFile') }}</span>
          </div>
          <div class="import-card-body">
            <label class="file-drop-area" :class="{ 'has-file': uploadFile }">
              <input type="file" accept=".zip" class="file-input-hidden" @change="onFileChange" />
              <span v-if="uploadFile" class="file-name">{{ uploadFile.name }}</span>
              <span v-else class="file-placeholder">
                <span class="file-icon">📂</span>
                {{ t('admin.sde.clickSelectZip') }}
              </span>
            </label>
            <div class="import-action">
              <n-button
                :loading="uploading || isRunning"
                :disabled="isRunning || !uploadFile"
                class="action-btn"
                @click="handleUpload"
              >
                {{ isRunning ? t('admin.sde.importing') : t('admin.sde.uploadAndImport') }}
              </n-button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="muted">{{ t('common.noData') }}</div>
  </div>
</template>

<style scoped>
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.count-bar { font-size: 0.85rem; color: #87867f; }

.sde-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-bottom: 12px; }
.sde-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 16px 18px;
}
.card-label { font-size: 0.78rem; color: #5e5d59; margin-bottom: 8px; }
.card-value { font-size: 1.4rem; font-weight: 500; color: #faf9f5; font-family: Georgia, serif; }
.card-value.small { font-size: 0.95rem; }

.task-status { font-size: 0.75rem; color: #87867f; margin-top: 4px; }

.source-url { font-size: 0.8rem; color: #5e5d59; margin-bottom: 12px; }
.source-url code { color: #87867f; font-family: monospace; }

.result-box {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 16px;
}
.result-title { font-size: 0.85rem; color: #b0aea5; margin-bottom: 10px; }
.result-grid { display: flex; gap: 24px; }
.result-item { display: flex; flex-direction: column; gap: 2px; }
.result-label { font-size: 0.72rem; color: #5e5d59; }
.result-value { font-size: 1rem; color: #faf9f5; font-family: Georgia, serif; }

.error-box {
  background: rgba(181, 51, 51, 0.1);
  border: 1px solid #b53333;
  border-radius: 6px;
  padding: 12px 16px;
  color: #faf9f5;
  font-size: 0.85rem;
  margin-bottom: 20px;
}

.import-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.import-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 12px;
  overflow: hidden;
}

.import-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-bottom: 1px solid #30302e;
  background: rgba(255,255,255,0.02);
}

.import-card-icon { font-size: 1rem; }

.import-card-title {
  font-family: Georgia, serif;
  font-size: 0.95rem;
  font-weight: 500;
  color: #faf9f5;
  letter-spacing: 0.01em;
}

.import-card-body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.url-display-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.url-label {
  font-size: 0.72rem;
  color: #5e5d59;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.url-code {
  font-family: monospace;
  font-size: 0.75rem;
  color: #87867f;
  word-break: break-all;
  background: rgba(255,255,255,0.04);
  border: 1px solid #30302e;
  border-radius: 6px;
  padding: 6px 10px;
  line-height: 1.5;
}

.import-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.import-checkbox { color: #b0aea5 !important; font-size: 0.88rem; }

.custom-url-input { flex: 1; min-width: 200px; }

.import-action { display: flex; justify-content: flex-end; }

.action-btn {
  background: #c96442 !important;
  color: #faf9f5 !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 0 18px !important;
  font-size: 0.88rem !important;
  height: 34px !important;
  box-shadow: #c96442 0px 0px 0px 0px, #c96442 0px 0px 0px 1px !important;
  transition: opacity 0.15s ease !important;
}
.action-btn:hover:not(:disabled) { opacity: 0.88 !important; }
.action-btn:disabled { background: #3d3d3a !important; color: #5e5d59 !important; box-shadow: none !important; cursor: not-allowed; }

.file-drop-area {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  border: 1px dashed #3d3d3a;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
  padding: 12px 16px;
}
.file-drop-area:hover { border-color: #c96442; background: rgba(201, 100, 66, 0.05); }
.file-drop-area.has-file { border-style: solid; border-color: #c96442; background: rgba(201, 100, 66, 0.07); }

.file-input-hidden { display: none; }

.file-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #5e5d59;
  font-size: 0.85rem;
}
.file-icon { font-size: 1.4rem; }

.file-name {
  font-size: 0.85rem;
  color: #b0aea5;
  font-family: monospace;
  word-break: break-all;
  text-align: center;
}

.muted { color: #5e5d59; }
</style>
