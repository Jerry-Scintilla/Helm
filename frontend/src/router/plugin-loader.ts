/**
 * iframe-based plugin route loader.
 *
 * For each enabled plugin that declares a frontend_url, registers a Vue Router
 * catch-all route pointing to PluginIframeView. The plugin's own SPA handles
 * internal navigation inside the iframe; Helm only manages the outer shell.
 */
import type { Router } from 'vue-router'
import api from '@/api'
import type { PluginInfo } from '@/stores/plugin'

// ── Route management ──────────────────────────────────────────────────────────

const _registeredPlugins = new Set<string>()

function removePluginRoutes(router: Router, pluginName: string): void {
  for (const route of router.getRoutes()) {
    if (route.meta?.pluginName === pluginName) {
      try {
        router.removeRoute(route.name!)
      } catch {
        /* already removed */
      }
    }
  }
  _registeredPlugins.delete(pluginName)
}

export async function loadPluginRoutes(router: Router): Promise<void> {
  try {
    const res = await api.get<PluginInfo[]>('/api/v1/plugins/')

    for (const plugin of res.data) {
      removePluginRoutes(router, plugin.name)

      if (!plugin.frontend_url) continue

      router.addRoute('main', {
        // Catch-all so the plugin's internal SPA routes don't cause Helm 404s
        path: `plugins/${plugin.name}/:pathMatch(.*)*`,
        name: plugin.name,
        component: () => import('@/views/plugin/PluginIframeView.vue'),
        meta: {
          pluginName: plugin.name,
          frontendUrl: plugin.frontend_url,
          iframePlugin: true,
        },
      })

      _registeredPlugins.add(plugin.name)
      console.info(`[PluginLoader] Registered iframe route for "${plugin.name}"`)
    }
  } catch (err) {
    console.warn('[PluginLoader] Failed to load plugin manifest:', err)
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
      } else if (ev.type === 'plugin.disabled' || ev.type === 'plugin.uninstalled') {
        if (ev.name) removePluginRoutes(router, ev.name)
      }
    } catch {
      /* ignore malformed events */
    }
  }

  return () => es.close()
}
