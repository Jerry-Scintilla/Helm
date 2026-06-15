import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface CharacterSubmoduleMeta {
  slug: string
  label: string
  icon: string
  order: number
  iframe_url_template: string
  required_permission?: string | null
}

export interface SidebarItemMeta {
  label: string
  route: string
  icon: string
  order: number
  required_permission?: string | null
}

export interface PluginMeta {
  esi_scopes: string[]
  sidebar_items: SidebarItemMeta[]
  widgets: Array<{ component: string; title: string; order: number }>
  character_submodules: CharacterSubmoduleMeta[]
}

export interface PluginInfo {
  id: number
  name: string
  package_name: string
  entry_point: string
  version: string
  author: string
  description: string
  helm_sdk_version: string
  is_enabled: boolean
  status: 'installed' | 'enabled' | 'disabled' | 'error' | 'uninstalled'
  error_message: string | null
  meta: PluginMeta
  frontend_url: string | null
  installed_at: string
  updated_at: string
}

export interface VersionInfo {
  version: string
  released_at: string | null
  yanked: boolean
  yanked_reason: string | null
}

export interface MarketplacePlugin {
  package_name: string
  display_name: string
  description: string
  author: string
  version: string | null
  tags: string[]
  verified: boolean
  homepage: string | null
  installed: boolean
  installed_version: string | null
  update_available: boolean
  source: 'pypi' | 'testpypi'
}

export const usePluginStore = defineStore('plugin', () => {
  const plugins = ref<PluginInfo[]>([])
  const installLog = ref<string[]>([])
  const installing = ref(false)
  const installSucceeded = ref(false)
  const uninstallInProgress = ref(false)
  const lastInstalledPlugin = ref<string | null>(null)
  const marketplacePlugins = ref<MarketplacePlugin[]>([])
  const marketplaceLoading = ref(false)
  const marketplaceRefreshing = ref(false)
  // Per-package version lists (with metadata) for the marketplace version
  // picker, keyed by package_name. Fetched lazily and cached.
  const marketplaceVersions = ref<Record<string, VersionInfo[]>>({})
  const versionsLoading = ref<Record<string, boolean>>({})
  // Tracks a cache-bust token (Unix ms timestamp) per plugin name.
  // Appended as ?_v=<token> to iframe src to force reload after status change.
  const pluginCacheTokens = ref<Record<string, number>>({})

  let _sse: EventSource | null = null

  function bumpCacheToken(name: string) {
    pluginCacheTokens.value = { ...pluginCacheTokens.value, [name]: Date.now() }
  }

  // Ensure a token exists for `name`. If unset (e.g. cold start before any
  // install/enable event), allocate one now so the iframe URL is unique to
  // this session — prevents the browser from re-using a stale cached document
  // left over from a previous session or a previous build of the plugin.
  function ensureCacheToken(name: string): number {
    const cur = pluginCacheTokens.value[name]
    if (cur !== undefined) return cur
    const t = Date.now()
    pluginCacheTokens.value = { ...pluginCacheTokens.value, [name]: t }
    return t
  }

  async function fetchPlugins() {
    const res = await api.get<PluginInfo[]>('/api/v1/admin/plugins/')
    plugins.value = res.data
  }

  async function fetchEnabledPlugins() {
    const res = await api.get<PluginInfo[]>('/api/v1/plugins/')
    // Merge: keep admin-fetched entries, supplement with public ones not yet loaded
    const existing = new Map(plugins.value.map(p => [p.name, p]))
    for (const p of res.data) {
      if (!existing.has(p.name)) existing.set(p.name, p)
    }
    plugins.value = Array.from(existing.values())
  }

  async function searchMarketplace(q: string) {
    marketplaceLoading.value = true
    try {
      const res = await api.get<MarketplacePlugin[]>(
        `/api/v1/admin/plugins/marketplace/search?q=${encodeURIComponent(q)}`,
      )
      marketplacePlugins.value = res.data
    } finally {
      marketplaceLoading.value = false
    }
  }

  async function refreshMarketplace() {
    marketplaceRefreshing.value = true
    try {
      await api.post('/api/v1/admin/plugins/marketplace/refresh')
    } finally {
      marketplaceRefreshing.value = false
    }
  }

  async function fetchVersions(packageName: string, source: 'pypi' | 'testpypi' = 'pypi') {
    if (!packageName) return
    // Cached or already loading → skip.
    if (marketplaceVersions.value[packageName] || versionsLoading.value[packageName]) return
    versionsLoading.value = { ...versionsLoading.value, [packageName]: true }
    try {
      const res = await api.get<{ versions: VersionInfo[] }>(
        '/api/v1/admin/plugins/marketplace/versions',
        { params: { package_name: packageName, source } },
      )
      marketplaceVersions.value = { ...marketplaceVersions.value, [packageName]: res.data.versions }
    } catch {
      marketplaceVersions.value = { ...marketplaceVersions.value, [packageName]: [] }
    } finally {
      versionsLoading.value = { ...versionsLoading.value, [packageName]: false }
    }
  }

  async function installByName(
    packageName: string,
    source: 'pypi' | 'testpypi' = 'pypi',
    version?: string | null,
  ) {
    await api.post('/api/v1/admin/plugins/install', {
      package_name: packageName,
      source,
      version: version || null,
    })
  }

  async function installByWhl(file: File) {
    const form = new FormData()
    form.append('file', file)
    await api.post('/api/v1/admin/plugins/install/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  async function enablePlugin(name: string) {
    await api.post(`/api/v1/admin/plugins/${name}/enable`)
    bumpCacheToken(name)
    await fetchPlugins()
  }

  async function disablePlugin(name: string) {
    await api.post(`/api/v1/admin/plugins/${name}/disable`)
    bumpCacheToken(name)
    await fetchPlugins()
  }

  // Holds the polling-fallback timer so we can cancel it if an SSE event
  // resolves the uninstall first (or the component unmounts).
  let _uninstallPoll: ReturnType<typeof setInterval> | null = null

  function stopUninstallPoll() {
    if (_uninstallPoll) {
      clearInterval(_uninstallPoll)
      _uninstallPoll = null
    }
  }

  async function uninstallPlugin(name: string, keepData = false) {
    uninstallInProgress.value = true
    bumpCacheToken(name)
    try {
      await api.delete(`/api/v1/admin/plugins/${name}`, { params: { keep_data: keepData } })
    } catch (e) {
      uninstallInProgress.value = false
      throw e
    }
    // Polling fallback: the backend finishes uninstall in a detached task and
    // announces it over SSE. If that event is missed (connection drop, queue
    // full, publish-before-subscribe), the UI would hang in "uninstalling"
    // forever. Poll the plugin's status endpoint — a 404 means the DB record
    // was deleted, i.e. the uninstall completed — and clear the state ourselves.
    stopUninstallPoll()
    let elapsed = 0
    let consecutiveErrors = 0
    const finish = async () => {
      stopUninstallPoll()
      uninstallInProgress.value = false
      bumpCacheToken(name)
      await fetchPlugins()
    }
    _uninstallPoll = setInterval(async () => {
      elapsed += 2000
      try {
        await api.get(`/api/v1/admin/plugins/${name}/status`)
        consecutiveErrors = 0
        // Still present → keep waiting (give up after 5 min as a safety valve).
        if (elapsed >= 300000) await finish()
      } catch (err: any) {
        const status = err?.response?.status
        if (status === 404) {
          // DB record gone → uninstall completed.
          await finish()
        } else if (status === 401 || status === 403) {
          // Session/permission lost — polling will never succeed; stop now.
          await finish()
        } else {
          // Transient (network / 5xx). Tolerate a few, then give up so we don't
          // hammer the API for the full 5 minutes.
          consecutiveErrors += 1
          if (consecutiveErrors >= 5) await finish()
        }
      }
    }, 2000)
  }

  function startSSE() {
    if (_sse) return
    const token = localStorage.getItem('access_token') ?? ''
    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    _sse = new EventSource(`${base}/api/v1/admin/plugins/events?token=${token}`)
    _sse.onmessage = async (e) => {
      try {
        const ev = JSON.parse(e.data) as { type: string; line?: string; name?: string }
        if (ev.type === 'plugin.install.log' && ev.line !== undefined) {
          installLog.value.push(ev.line)
        } else if (ev.type === 'plugin.installed') {
          if (ev.name) {
            bumpCacheToken(ev.name)
            lastInstalledPlugin.value = ev.name
          }
          await fetchPlugins()
          installing.value = false
          installSucceeded.value = true
        } else if (ev.type === 'plugin.uninstalled') {
          stopUninstallPoll()
          uninstallInProgress.value = false
          if (ev.name) bumpCacheToken(ev.name)
          fetchPlugins()
        } else if (ev.type === 'plugin.enabled' || ev.type === 'plugin.disabled') {
          if (ev.name) bumpCacheToken(ev.name)
          fetchPlugins()
        } else if (ev.type === 'plugin.installing') {
          installing.value = true
          installSucceeded.value = false
          installLog.value = []
        } else if (ev.type === 'plugin.install.failed') {
          installing.value = false
          installSucceeded.value = false
        }
      } catch {
        // ignore malformed messages
      }
    }
    _sse.onerror = () => {
      // SSE reconnects automatically; reset installing state if connection drops
      installing.value = false
    }
  }

  function stopSSE() {
    _sse?.close()
    _sse = null
    stopUninstallPoll()
  }

  return {
    plugins,
    installLog,
    installing,
    installSucceeded,
    uninstallInProgress,
    lastInstalledPlugin,
    pluginCacheTokens,
    marketplacePlugins,
    marketplaceLoading,
    marketplaceRefreshing,
    marketplaceVersions,
    versionsLoading,
    fetchVersions,
    bumpCacheToken,
    ensureCacheToken,
    fetchPlugins,
    fetchEnabledPlugins,
    searchMarketplace,
    refreshMarketplace,
    installByName,
    installByWhl,
    enablePlugin,
    disablePlugin,
    uninstallPlugin,
    startSSE,
    stopSSE,
  }
})
