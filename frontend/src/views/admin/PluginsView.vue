<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { usePluginStore } from '@/stores/plugin'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'

const store = usePluginStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)

// Install modal
const showInstall = ref(false)
const installTab = ref<'pypi' | 'whl'>('pypi')
const packageName = ref('')
const whlFile = ref<File | null>(null)
const logContainer = ref<HTMLElement | null>(null)

// Uninstall confirm modal
const showUninstall = ref(false)
const uninstallTarget = ref('')

onMounted(async () => {
  store.startSSE()
  try {
    await store.fetchPlugins()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  store.stopSSE()
})

watch(() => store.installing, (cur, prev) => {
  if (prev && !cur && showInstall.value) {
    if (store.installSucceeded) {
      showInstall.value = false
      message.success(t('admin.plugins.installSuccess'))
    } else {
      message.error(t('admin.plugins.installFailed'))
    }
  }
})

async function handleInstall() {
  if (installTab.value === 'pypi') {
    if (!packageName.value.trim()) return
    try {
      await store.installByName(packageName.value.trim())
    } catch {
      message.error(t('admin.plugins.submitFailed'))
    }
  } else {
    if (!whlFile.value) return
    try {
      await store.installByWhl(whlFile.value)
    } catch {
      message.error(t('admin.plugins.submitFailed'))
    }
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  whlFile.value = input.files?.[0] ?? null
}

function openUninstall(name: string) {
  uninstallTarget.value = name
  showUninstall.value = true
}

watch(() => store.uninstallInProgress, (cur, prev) => {
  if (prev && !cur && showUninstall.value) {
    showUninstall.value = false
    message.success(t('admin.plugins.uninstallSuccess', { name: uninstallTarget.value }))
  }
})

async function confirmUninstall() {
  try {
    await store.uninstallPlugin(uninstallTarget.value)
  } catch {
    message.error(t('admin.plugins.uninstallFailed'))
  }
}

async function toggleEnable(name: string, enabled: boolean) {
  try {
    if (enabled) {
      await store.disablePlugin(name)
      message.success(t('common.disable'))
    } else {
      await store.enablePlugin(name)
      message.success(t('common.enable'))
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail ?? t('common.operationFailed'))
  }
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    enabled: '#6abf69',
    disabled: '#87867f',
    error: '#b53333',
    installed: '#c96442',
    uninstalled: '#5e5d59',
  }
  return map[status] ?? '#5e5d59'
}

function statusLabel(status: string) {
  const keys: Record<string, string> = {
    enabled: 'admin.plugins.statusEnabled',
    disabled: 'admin.plugins.statusDisabled',
    error: 'admin.plugins.statusError',
    installed: 'admin.plugins.statusInstalled',
    uninstalled: 'admin.plugins.statusUninstalled',
  }
  return keys[status] ? t(keys[status] as any) : status
}

// Auto-scroll log to bottom
function scrollLog() {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="section-header">
      <span class="count-bar">{{ t('admin.plugins.count', { n: store.plugins.length }) }}</span>
      <button class="btn-primary" @click="showInstall = true">{{ t('admin.plugins.install') }}</button>
    </div>

    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />

    <!-- Plugin cards -->
    <div v-if="!loading" class="plugin-grid">
      <div v-if="store.plugins.length === 0" class="empty-hint">
        {{ t('admin.plugins.empty') }}
      </div>
      <div v-for="p in store.plugins" :key="p.id" class="plugin-card">
        <div class="plugin-top">
          <div class="plugin-info">
            <div class="plugin-name">{{ p.name }}</div>
            <div class="plugin-meta">v{{ p.version }} · {{ p.author || t('admin.plugins.unknownAuthor') }}</div>
          </div>
          <span class="status-tag" :style="{ color: statusColor(p.status), background: `${statusColor(p.status)}18` }">
            {{ statusLabel(p.status) }}
          </span>
        </div>
        <div class="plugin-desc">{{ p.description || t('admin.plugins.noDesc') }}</div>
        <div v-if="p.error_message" class="plugin-error">{{ p.error_message }}</div>
        <div class="plugin-actions">
          <button
            v-if="p.status !== 'uninstalled'"
            class="btn-sm"
            @click="toggleEnable(p.name, p.is_enabled)"
          >
            {{ p.is_enabled ? t('common.disable') : t('common.enable') }}
          </button>
          <button class="btn-sm btn-danger" @click="openUninstall(p.name)">{{ t('admin.plugins.uninstall') }}</button>
        </div>
      </div>
    </div>

    <!-- Install modal -->
    <n-modal v-model:show="showInstall" preset="card" :title="t('admin.plugins.installModalTitle')" style="width:520px;max-width:95vw">
      <div class="install-tabs">
        <button :class="['tab-btn', installTab === 'pypi' && 'active']" @click="installTab = 'pypi'">{{ t('admin.plugins.pypiTab') }}</button>
        <button :class="['tab-btn', installTab === 'whl' && 'active']" @click="installTab = 'whl'">{{ t('admin.plugins.whlTab') }}</button>
      </div>

      <div v-if="installTab === 'pypi'" class="tab-body">
        <n-input v-model:value="packageName" placeholder="例如：helm-plugin-mcp" clearable />
      </div>
      <div v-else class="tab-body">
        <label class="file-drop">
          <input type="file" accept=".whl" style="display:none" @change="onFileChange" />
          <span v-if="!whlFile" class="file-hint">{{ t('admin.plugins.dropWhl') }}</span>
          <span v-else class="file-name">{{ whlFile.name }}</span>
        </label>
      </div>

      <!-- Install log -->
      <div v-if="store.installLog.length > 0 || store.installing" class="log-wrap">
        <div class="log-label">{{ t('admin.plugins.installLog') }}</div>
        <pre ref="logContainer" class="log-pre" @vue:updated="scrollLog">{{ store.installLog.join('\n') }}</pre>
      </div>

      <template #footer>
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <n-button @click="showInstall = false">{{ t('common.close') }}</n-button>
          <button class="btn-primary" :disabled="store.installing" @click="handleInstall">
            {{ store.installing ? t('admin.plugins.installing') : t('admin.plugins.startInstall') }}
          </button>
        </div>
      </template>
    </n-modal>

    <!-- Uninstall confirm modal -->
    <n-modal
      v-model:show="showUninstall"
      preset="card"
      :title="t('admin.plugins.confirmUninstall')"
      style="width:400px;max-width:95vw"
      :mask-closable="!store.uninstallInProgress"
      :close-on-esc="!store.uninstallInProgress"
    >
      <p class="confirm-text" v-html="t('admin.plugins.uninstallWarning', { name: `<strong>${uninstallTarget}</strong>` })" />
      <template #footer>
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <n-button :disabled="store.uninstallInProgress" @click="showUninstall = false">{{ t('common.cancel') }}</n-button>
          <n-button type="error" :loading="store.uninstallInProgress" @click="confirmUninstall">{{ t('admin.plugins.confirmUninstallBtn') }}</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.count-bar { font-size: 0.85rem; color: #87867f; }

.btn-primary {
  background: #c96442;
  color: #faf9f5;
  border: none;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 0.88rem;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-primary:hover { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.plugin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }

.empty-hint {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px 0;
  color: #5e5d59;
  font-size: 0.9rem;
}

.plugin-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plugin-top { display: flex; justify-content: space-between; align-items: flex-start; }
.plugin-info { flex: 1; min-width: 0; }
.plugin-name { font-size: 0.95rem; font-weight: 500; color: #faf9f5; margin-bottom: 2px; }
.plugin-meta { font-size: 0.75rem; color: #87867f; }

.status-tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
  margin-left: 8px;
}

.plugin-desc { font-size: 0.82rem; color: #87867f; line-height: 1.5; }
.plugin-error { font-size: 0.78rem; color: #b53333; background: rgba(181,51,51,0.1); padding: 6px 10px; border-radius: 4px; }

.plugin-actions { display: flex; gap: 8px; margin-top: 4px; }
.btn-sm {
  background: #30302e;
  color: #b0aea5;
  border: none;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-sm:hover { background: #3d3d3a; }
.btn-danger { color: #b53333; }
.btn-danger:hover { background: rgba(181,51,51,0.15); }

/* Install modal */
.install-tabs { display: flex; gap: 0; border-bottom: 1px solid #30302e; margin-bottom: 16px; }
.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 6px 16px;
  font-size: 0.85rem;
  color: #87867f;
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}
.tab-btn:hover { color: #b0aea5; }
.tab-btn.active { color: #faf9f5; border-bottom-color: #c96442; }

.tab-body { margin-bottom: 16px; }

.file-drop {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  border: 1px dashed #30302e;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.file-drop:hover { border-color: #c96442; }
.file-hint { font-size: 0.85rem; color: #5e5d59; }
.file-name { font-size: 0.85rem; color: #c96442; }

.log-wrap { margin-top: 8px; }
.log-label { font-size: 0.75rem; color: #5e5d59; margin-bottom: 6px; }
.log-pre {
  background: #141413;
  border: 1px solid #30302e;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 0.75rem;
  color: #b0aea5;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  font-family: 'Anthropic Mono', monospace;
}

.confirm-text { font-size: 0.9rem; color: #b0aea5; line-height: 1.6; }
.confirm-text :deep(strong) { color: #faf9f5; }
</style>
