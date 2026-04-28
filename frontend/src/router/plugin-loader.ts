/**
 * Plugin dynamic route loader.
 * Phase 3: loads plugin metadata and registers routes for plugins that have
 * a frontend_bundle_url. Actual bundle import() is the Phase 4 protocol.
 */
import type { Router } from 'vue-router'
import api from '@/api'
import type { PluginInfo } from '@/stores/plugin'

let _sseCleanup: (() => void) | null = null

export async function loadPluginRoutes(router: Router): Promise<void> {
  try {
    const res = await api.get<PluginInfo[]>('/api/v1/plugins/')
    for (const plugin of res.data) {
      if (!plugin.frontend_bundle_url) continue
      try {
        // Phase 4: dynamically import the plugin's frontend bundle
        // const module = await import(/* @vite-ignore */ plugin.frontend_bundle_url)
        // if (module.routes) {
        //   for (const route of module.routes) router.addRoute(route)
        // }
        console.info(`[PluginLoader] Plugin "${plugin.name}" has bundle at ${plugin.frontend_bundle_url} (Phase 4 import)`)
      } catch (err) {
        console.warn(`[PluginLoader] Failed to load bundle for plugin "${plugin.name}":`, err)
      }
    }
  } catch (err) {
    console.warn('[PluginLoader] Failed to fetch plugin manifest:', err)
  }
}

export function setupPluginSSEReload(router: Router): () => void {
  const token = localStorage.getItem('access_token') ?? ''
  const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
  const es = new EventSource(`${base}/api/v1/admin/plugins/events?token=${token}`)

  es.onmessage = async (e) => {
    try {
      const ev = JSON.parse(e.data) as { type: string; name?: string }
      if (ev.type === 'plugin.installed' || ev.type === 'plugin.enabled') {
        await loadPluginRoutes(router)
      }
      // plugin.uninstalled / plugin.disabled: routes remain registered until page reload
      // (router.removeRoute requires knowing the route name; Phase 4 will track this)
    } catch {
      // ignore
    }
  }

  const cleanup = () => es.close()
  _sseCleanup = cleanup
  return cleanup
}
