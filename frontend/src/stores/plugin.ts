import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface CharacterSubmoduleMeta {
  slug: string
  label: string
  icon: string
  order: number
  iframe_url_template: string
}

export interface PluginMeta {
  esi_scopes: string[]
  sidebar_items: Array<{ label: string; route: string; icon: string; order: number }>
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

export const usePluginStore = defineStore('plugin', () => {
  const plugins = ref<PluginInfo[]>([])
  const installLog = ref<string[]>([])
  const installing = ref(false)
  const installSucceeded = ref(false)
  const uninstallInProgress = ref(false)
  const lastInstalledPlugin = ref<string | null>(null)
  // Tracks a cache-bust token (Unix ms timestamp) per plugin name.
  // Appended as ?_v=<token> to iframe src to force reload after status change.
  const pluginCacheTokens = ref<Record<string, number>>({})

  let _sse: EventSource | null = null

  function bumpCacheToken(name: string) {
    pluginCacheTokens.value = { ...pluginCacheTokens.value, [name]: Date.now() }
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

  async function installByName(packageName: string) {
    await api.post('/api/v1/admin/plugins/install', { package_name: packageName })
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

  async function uninstallPlugin(name: string) {
    uninstallInProgress.value = true
    bumpCacheToken(name)
    try {
      await api.delete(`/api/v1/admin/plugins/${name}`)
    } catch (e) {
      uninstallInProgress.value = false
      throw e
    }
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
  }

  return {
    plugins,
    installLog,
    installing,
    installSucceeded,
    uninstallInProgress,
    lastInstalledPlugin,
    pluginCacheTokens,
    fetchPlugins,
    fetchEnabledPlugins,
    installByName,
    installByWhl,
    enablePlugin,
    disablePlugin,
    uninstallPlugin,
    startSSE,
    stopSSE,
  }
})
