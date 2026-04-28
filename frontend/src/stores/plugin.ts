import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface PluginMeta {
  esi_scopes: string[]
  sidebar_items: Array<{ label: string; route: string; icon: string; order: number }>
  widgets: Array<{ component: string; title: string; order: number }>
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
  frontend_bundle_url: string | null
  installed_at: string
  updated_at: string
}

export const usePluginStore = defineStore('plugin', () => {
  const plugins = ref<PluginInfo[]>([])
  const installLog = ref<string[]>([])
  const installing = ref(false)

  let _sse: EventSource | null = null

  async function fetchPlugins() {
    const res = await api.get<PluginInfo[]>('/api/v1/admin/plugins/')
    plugins.value = res.data
  }

  async function installByName(packageName: string) {
    installing.value = true
    installLog.value = []
    try {
      await api.post('/api/v1/admin/plugins/install', { package_name: packageName })
    } finally {
      installing.value = false
    }
  }

  async function installByWhl(file: File) {
    installing.value = true
    installLog.value = []
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/api/v1/admin/plugins/install/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    } finally {
      installing.value = false
    }
  }

  async function enablePlugin(name: string) {
    await api.post(`/api/v1/admin/plugins/${name}/enable`)
    await fetchPlugins()
  }

  async function disablePlugin(name: string) {
    await api.post(`/api/v1/admin/plugins/${name}/disable`)
    await fetchPlugins()
  }

  async function uninstallPlugin(name: string, pipRemove = false) {
    await api.delete(`/api/v1/admin/plugins/${name}`, { params: { pip_remove: pipRemove } })
    await fetchPlugins()
  }

  function startSSE() {
    if (_sse) return
    const token = localStorage.getItem('access_token') ?? ''
    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    _sse = new EventSource(`${base}/api/v1/admin/plugins/events?token=${token}`)
    _sse.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as { type: string; line?: string }
        if (ev.type === 'plugin.install.log' && ev.line !== undefined) {
          installLog.value.push(ev.line)
        } else if (
          ev.type === 'plugin.installed' ||
          ev.type === 'plugin.enabled' ||
          ev.type === 'plugin.disabled' ||
          ev.type === 'plugin.uninstalled'
        ) {
          fetchPlugins()
        } else if (ev.type === 'plugin.installing') {
          installing.value = true
          installLog.value = []
        } else if (ev.type === 'plugin.install.failed') {
          installing.value = false
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
    fetchPlugins,
    installByName,
    installByWhl,
    enablePlugin,
    disablePlugin,
    uninstallPlugin,
    startSSE,
    stopSSE,
  }
})
