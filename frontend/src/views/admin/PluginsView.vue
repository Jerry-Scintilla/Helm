<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { usePluginStore, type MarketplacePlugin } from '@/stores/plugin'
import { useAuthStore } from '@/stores/auth'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import HelmLoader from '@/components/HelmLoader.vue'

const store = usePluginStore()
const auth = useAuthStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)

// Top-level view tab: installed | marketplace
const viewTab = ref<'installed' | 'marketplace'>('installed')

// Marketplace search
const marketplaceQuery = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

function onMarketplaceTabEnter() {
  if (store.marketplacePlugins.length === 0) {
    store.searchMarketplace('')
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.searchMarketplace(marketplaceQuery.value)
  }, 350)
}

// Install modal (manual install: PyPI package name or .whl upload)
const showInstall = ref(false)
const installTab = ref<'pypi' | 'whl'>('pypi')
const packageName = ref('')
const whlFile = ref<File | null>(null)
const logContainer = ref<HTMLElement | null>(null)

function openInstallModal() {
  packageName.value = ''
  installTab.value = 'pypi'
  showInstall.value = true
}

// Version-selection modal: lists every available version with release date and
// status so the user can compare and pick one to install.
const showVersions = ref(false)
const versionsTarget = ref<MarketplacePlugin | null>(null)

function openVersions(pkg: MarketplacePlugin) {
  versionsTarget.value = pkg
  showVersions.value = true
  store.fetchVersions(pkg.package_name, pkg.source)
}

// The newest non-yanked version is the "latest" we badge in the list.
const latestVersion = computed(() => {
  const list = versionsTarget.value ? store.marketplaceVersions[versionsTarget.value.package_name] : undefined
  return list?.find(v => !v.yanked)?.version ?? null
})

function formatDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : ''
}

// Uninstall confirm modal
const showUninstall = ref(false)
const uninstallTarget = ref('')
const uninstallKeepData = ref(false)

// Re-login reminder modal
const showReloginModal = ref(false)
const reloginPluginName = ref('')
const missingScopes = ref<string[]>([])

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
  if (searchTimer) clearTimeout(searchTimer)
})

watch(() => store.installing, async (cur, prev) => {
  if (prev && !cur && showInstall.value) {
    if (store.installSucceeded) {
      showInstall.value = false
      message.success(t('admin.plugins.installSuccess'))
      if (store.lastInstalledPlugin) {
        await checkNewScopes(store.lastInstalledPlugin)
      }
    } else {
      message.error(t('admin.plugins.installFailed'))
    }
  }
})

// After a successful install, re-fetch marketplace so the installed badge updates.
watch(() => store.plugins, () => {
  if (store.marketplacePlugins.length > 0) {
    store.searchMarketplace(marketplaceQuery.value)
  }
})

async function checkNewScopes(pluginName: string) {
  const plugin = store.plugins.find(p => p.name === pluginName)
  if (!plugin?.meta?.esi_scopes?.length) return
  if (!auth.characterId) return
  try {
    const res = await api.get<{ scopes: string }>(`/api/v1/characters/${auth.characterId}/`)
    const granted = new Set(res.data.scopes.split(' ').filter(Boolean))
    const missing = plugin.meta.esi_scopes.filter(s => !granted.has(s))
    if (missing.length > 0) {
      reloginPluginName.value = pluginName
      missingScopes.value = missing
      showReloginModal.value = true
    }
  } catch {
    // best-effort; never block the UI
  }
}

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

// Install a specific version picked from the version modal ('' = latest).
// Closes the version modal and opens the install modal to stream the log.
async function installAtVersion(version: string) {
  const pkg = versionsTarget.value
  if (!pkg) return
  showVersions.value = false
  packageName.value = pkg.package_name
  installTab.value = 'pypi'
  showInstall.value = true
  try {
    await store.installByName(pkg.package_name, pkg.source, version || '')
  } catch {
    message.error(t('admin.plugins.submitFailed'))
  }
}

async function handleRefreshMarketplace() {
  try {
    await store.refreshMarketplace()
    await store.searchMarketplace(marketplaceQuery.value)
    message.success(t('admin.plugins.marketRefreshDone'))
  } catch {
    message.error(t('admin.plugins.marketRefreshFailed'))
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  whlFile.value = input.files?.[0] ?? null
}

function openUninstall(name: string) {
  uninstallTarget.value = name
  uninstallKeepData.value = false
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
    await store.uninstallPlugin(uninstallTarget.value, uninstallKeepData.value)
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
      await checkNewScopes(name)
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
    <!-- View tab bar -->
    <div class="view-tabs">
      <button
        :class="['view-tab', viewTab === 'installed' && 'active']"
        @click="viewTab = 'installed'"
      >{{ t('admin.plugins.tabInstalled') }}</button>
      <button
        :class="['view-tab', viewTab === 'marketplace' && 'active']"
        @click="viewTab = 'marketplace'; onMarketplaceTabEnter()"
      >{{ t('admin.plugins.tabMarketplace') }}</button>

      <div class="view-tab-spacer" />

      <button v-if="viewTab === 'installed'" class="btn-primary" @click="openInstallModal()">
        {{ t('admin.plugins.install') }}
      </button>
    </div>

    <!-- ── Installed tab ── -->
    <template v-if="viewTab === 'installed'">
      <div v-if="loading" class="helm-section-loader"><HelmLoader :size="48" /></div>

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
    </template>

    <!-- ── Marketplace tab ── -->
    <template v-else>
      <div class="market-search-bar">
        <input
          v-model="marketplaceQuery"
          class="market-search-input"
          :placeholder="t('admin.plugins.marketSearchPlaceholder')"
          @input="onSearchInput"
        />
        <span v-if="store.marketplaceLoading" class="market-searching">
          {{ t('admin.plugins.marketSearching') }}
        </span>
        <button
          class="btn-sm market-refresh-btn"
          :disabled="store.marketplaceRefreshing || store.marketplaceLoading"
          @click="handleRefreshMarketplace"
        >
          {{ store.marketplaceRefreshing ? t('admin.plugins.marketRefreshing') : t('admin.plugins.marketRefresh') }}
        </button>
      </div>

      <div v-if="store.marketplaceLoading && store.marketplacePlugins.length === 0" class="helm-section-loader">
        <HelmLoader :size="48" />
      </div>

      <div v-else class="plugin-grid">
        <div v-if="store.marketplacePlugins.length === 0 && !store.marketplaceLoading" class="empty-hint">
          {{ t('admin.plugins.marketEmpty') }}
        </div>
        <div v-for="p in store.marketplacePlugins" :key="p.package_name" class="plugin-card">
          <div class="plugin-top">
            <div class="plugin-info">
              <div class="plugin-name">
                {{ p.display_name }}
                <span v-if="p.verified" class="verified-badge">✓ {{ t('admin.plugins.verified') }}</span>
                <span class="source-badge" :class="p.source === 'testpypi' ? 'source-test' : 'source-prod'">
                  {{ p.source === 'testpypi' ? t('admin.plugins.sourceTestPypi') : t('admin.plugins.sourcePypi') }}
                </span>
              </div>
              <div class="plugin-meta">
                {{ p.package_name }}
                <template v-if="p.update_available"> · v{{ p.installed_version }} → v{{ p.version }}</template>
                <template v-else-if="p.version"> · v{{ p.version }}</template>
                <template v-if="p.author"> · {{ p.author }}</template>
              </div>
            </div>
            <span v-if="p.update_available" class="status-tag update-tag">
              {{ t('admin.plugins.marketUpdatable') }}
            </span>
            <span v-else-if="p.installed" class="status-tag installed-tag">
              {{ t('admin.plugins.marketInstalled') }}
            </span>
          </div>

          <div class="plugin-desc">{{ p.description || t('admin.plugins.noDesc') }}</div>

          <div v-if="p.tags.length > 0" class="tag-list">
            <span v-for="tag in p.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>

          <div class="plugin-actions">
            <a
              v-if="p.homepage"
              :href="p.homepage"
              target="_blank"
              rel="noopener"
              class="btn-sm"
            >{{ t('admin.plugins.marketHomepage') }}</a>
            <button
              class="btn-primary btn-sm-primary"
              :disabled="store.installing"
              @click="openVersions(p)"
            >
              {{ p.update_available
                ? t('admin.plugins.marketUpdate')
                : p.installed
                  ? t('admin.plugins.marketVersions')
                  : t('admin.plugins.marketInstall') }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Version selection modal -->
    <n-modal
      v-model:show="showVersions"
      preset="card"
      :title="t('admin.plugins.versionModalTitle')"
      style="width:560px;max-width:95vw"
    >
      <template v-if="versionsTarget">
        <div class="ver-header">
          <div class="ver-title">{{ versionsTarget.display_name }}</div>
          <div class="ver-pkg">{{ versionsTarget.package_name }}</div>
          <div v-if="versionsTarget.description" class="ver-desc">{{ versionsTarget.description }}</div>
          <div v-if="versionsTarget.installed_version" class="ver-installed">
            {{ t('admin.plugins.versionCurrentlyInstalled', { version: versionsTarget.installed_version }) }}
          </div>
        </div>

        <div v-if="store.versionsLoading[versionsTarget.package_name]" class="ver-loading">
          <HelmLoader :size="36" />
        </div>

        <div
          v-else-if="(store.marketplaceVersions[versionsTarget.package_name] || []).length === 0"
          class="ver-empty"
        >
          {{ t('admin.plugins.versionNone') }}
        </div>

        <ul v-else class="ver-list">
          <li
            v-for="v in store.marketplaceVersions[versionsTarget.package_name]"
            :key="v.version"
            class="ver-row"
            :class="{ 'ver-row-current': v.version === versionsTarget.installed_version }"
          >
            <div class="ver-row-main">
              <div class="ver-row-top">
                <span class="ver-num">v{{ v.version }}</span>
                <span v-if="v.version === latestVersion" class="ver-badge ver-badge-latest">{{ t('admin.plugins.versionLatestBadge') }}</span>
                <span v-if="v.version === versionsTarget.installed_version" class="ver-badge ver-badge-installed">{{ t('admin.plugins.versionInstalledBadge') }}</span>
                <span v-if="v.yanked" class="ver-badge ver-badge-yanked" :title="v.yanked_reason || ''">{{ t('admin.plugins.versionYankedBadge') }}</span>
              </div>
              <div class="ver-row-sub">
                <span v-if="v.released_at">{{ formatDate(v.released_at) }}</span>
                <span v-if="v.yanked && v.yanked_reason" class="ver-yank-reason">· {{ v.yanked_reason }}</span>
              </div>
            </div>
            <button
              class="btn-sm ver-install-btn"
              :class="{ 'ver-install-current': v.version === versionsTarget.installed_version }"
              :disabled="store.installing || v.version === versionsTarget.installed_version"
              @click="installAtVersion(v.version)"
            >
              {{ v.version === versionsTarget.installed_version
                ? t('admin.plugins.versionCurrent')
                : t('admin.plugins.marketInstall') }}
            </button>
          </li>
        </ul>
      </template>
    </n-modal>

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
      <label class="keep-data-row">
        <input type="checkbox" v-model="uninstallKeepData" :disabled="store.uninstallInProgress" />
        <span>
          <span class="keep-data-label">{{ t('admin.plugins.keepData') }}</span>
          <span class="keep-data-hint">{{ t('admin.plugins.keepDataHint') }}</span>
        </span>
      </label>
      <template #footer>
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <n-button :disabled="store.uninstallInProgress" @click="showUninstall = false">{{ t('common.cancel') }}</n-button>
          <n-button type="error" :loading="store.uninstallInProgress" @click="confirmUninstall">{{ t('admin.plugins.confirmUninstallBtn') }}</n-button>
        </div>
      </template>
    </n-modal>

    <!-- Re-login reminder modal -->
    <n-modal
      v-model:show="showReloginModal"
      preset="card"
      :title="t('admin.plugins.reloginRequired')"
      style="width:480px;max-width:95vw"
    >
      <p class="relogin-desc" v-html="t('admin.plugins.reloginDesc', { name: `<strong>${reloginPluginName}</strong>` })" />
      <ul class="scope-list">
        <li v-for="scope in missingScopes" :key="scope" class="scope-item">{{ scope }}</li>
      </ul>
      <template #footer>
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <n-button @click="showReloginModal = false">{{ t('admin.plugins.reloginLater') }}</n-button>
          <button class="btn-primary" @click="auth.loginWithEve()">{{ t('admin.plugins.reloginNow') }}</button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
/* View tab bar */
.view-tabs {
  display: flex;
  align-items: center;
  gap: 0;
  border-bottom: 1px solid #30302e;
  margin-bottom: 16px;
}
.view-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 6px 18px;
  font-size: 0.88rem;
  color: #87867f;
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}
.view-tab:hover { color: #b0aea5; }
.view-tab.active { color: #faf9f5; border-bottom-color: #c96442; }
.view-tab-spacer { flex: 1; }

/* Marketplace search */
.market-search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.market-search-input {
  flex: 1;
  max-width: 360px;
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 0.85rem;
  color: #faf9f5;
  outline: none;
  transition: border-color 0.15s;
}
.market-search-input::placeholder { color: #5e5d59; }
.market-search-input:focus { border-color: #3898ec; }
.market-searching { font-size: 0.78rem; color: #5e5d59; }

/* Verified badge */
.verified-badge {
  display: inline-block;
  font-size: 0.68rem;
  background: rgba(106, 191, 105, 0.12);
  color: #6abf69;
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
  vertical-align: middle;
}

/* Installed badge in marketplace */
.installed-tag {
  color: #6abf69;
  background: rgba(106, 191, 105, 0.1) !important;
}

/* Update-available badge in marketplace */
.update-tag {
  color: #c96442;
  background: rgba(201, 100, 66, 0.12) !important;
}

/* Keep-data checkbox in uninstall modal */
.keep-data-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 14px;
  cursor: pointer;
}
.keep-data-row input { margin-top: 3px; flex-shrink: 0; cursor: pointer; }
.keep-data-label { display: block; font-size: 0.85rem; color: #faf9f5; }
.keep-data-hint { display: block; font-size: 0.75rem; color: #87867f; line-height: 1.5; margin-top: 2px; }

/* Source registry badge */
.source-badge {
  display: inline-block;
  font-size: 0.62rem;
  border-radius: 3px;
  padding: 1px 5px;
  margin-left: 5px;
  vertical-align: middle;
  font-weight: 400;
}
.source-prod {
  background: rgba(56, 152, 236, 0.12);
  color: #3898ec;
}
.source-test {
  background: rgba(201, 100, 66, 0.12);
  color: #c96442;
}

/* Marketplace refresh button */
.market-refresh-btn {
  flex-shrink: 0;
}
.market-refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Tag chips */
.tag-list { display: flex; flex-wrap: wrap; gap: 4px; }
.tag {
  font-size: 0.68rem;
  background: #30302e;
  color: #87867f;
  border-radius: 4px;
  padding: 2px 7px;
}

/* Small primary button variant (in cards) */
.btn-sm-primary {
  background: #c96442;
  color: #faf9f5;
  border: none;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-sm-primary:hover { opacity: 0.88; }
.btn-sm-primary:disabled { opacity: 0.45; cursor: not-allowed; }

/* ── Shared styles (unchanged from original) ── */
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

.plugin-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; align-items: center; }
.btn-sm {
  background: #30302e;
  color: #b0aea5;
  border: none;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.15s;
  text-decoration: none;
  display: inline-block;
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

/* Version selection modal */
.ver-header { margin-bottom: 14px; }
.ver-title { font-size: 1rem; font-weight: 500; color: #faf9f5; }
.ver-pkg { font-size: 0.75rem; color: #87867f; font-family: 'Anthropic Mono', monospace; margin-top: 2px; }
.ver-desc { font-size: 0.82rem; color: #b0aea5; line-height: 1.5; margin-top: 8px; }
.ver-installed { font-size: 0.78rem; color: #6abf69; margin-top: 8px; }

.ver-loading { display: flex; justify-content: center; padding: 32px 0; }
.ver-empty { text-align: center; color: #5e5d59; font-size: 0.85rem; padding: 32px 0; }

.ver-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ver-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 10px 14px;
}
.ver-row-current { border-color: rgba(106, 191, 105, 0.4); }
.ver-row-main { min-width: 0; }
.ver-row-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ver-num { font-size: 0.9rem; font-weight: 500; color: #faf9f5; }
.ver-badge { font-size: 0.62rem; border-radius: 3px; padding: 1px 6px; }
.ver-badge-latest { color: #3898ec; background: rgba(56, 152, 236, 0.12); }
.ver-badge-installed { color: #6abf69; background: rgba(106, 191, 105, 0.12); }
.ver-badge-yanked { color: #b53333; background: rgba(181, 51, 51, 0.12); }
.ver-row-sub { font-size: 0.72rem; color: #87867f; margin-top: 3px; }
.ver-yank-reason { color: #b53333; }

.ver-install-btn { flex-shrink: 0; }
.ver-install-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ver-install-current { background: transparent; color: #6abf69; }

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

.relogin-desc { font-size: 0.88rem; color: #b0aea5; line-height: 1.6; margin: 0 0 12px; }
.relogin-desc :deep(strong) { color: #faf9f5; }
.scope-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; }
.scope-item {
  font-size: 0.75rem;
  font-family: 'Anthropic Mono', monospace;
  background: #141413;
  border: 1px solid #30302e;
  border-radius: 4px;
  padding: 4px 10px;
  color: #c96442;
}
</style>
