import { onMounted, onUnmounted, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { onAccessTokenRefreshed, refreshAccessToken } from '@/api'
import { useLocaleStore } from '@/stores/locale'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
// Retry helm:init at these offsets so a plugin SPA that registers its
// message listener after iframe @load fires still receives the init payload.
// Stops once the plugin posts helm:ready (or any message that implies it is
// listening).
const INIT_RETRY_OFFSETS_MS = [150, 500, 1500, 3000]

/**
 * Shared host-side message protocol used by PluginIframeView and
 * CharacterSubmoduleView. Handles:
 *   - helm:init handshake with retry to survive plugin SPA bootstrap races
 *   - helm:token:expired → actually refreshes the token (was previously
 *     bouncing the same stale token back, causing a 401 loop)
 *   - helm:navigate
 *   - Broadcasts helm:token:refreshed when the parent's axios interceptor
 *     refreshes the token, so already-loaded plugins pick up the new one.
 */
export function useIframePluginHost(iframeRef: Ref<HTMLIFrameElement | undefined>) {
  const router = useRouter()
  const localeStore = useLocaleStore()

  let ackReceived = false
  const retryTimers: number[] = []

  function postToIframe(message: unknown) {
    iframeRef.value?.contentWindow?.postMessage(message, '*')
  }

  function sendInit() {
    postToIframe({
      type: 'helm:init',
      payload: {
        token: localStorage.getItem('access_token'),
        apiBase: API_BASE,
        locale: localeStore.locale,
      },
    })
  }

  function clearRetries() {
    retryTimers.forEach((id) => window.clearTimeout(id))
    retryTimers.length = 0
  }

  function scheduleInitRetries() {
    clearRetries()
    ackReceived = false
    for (const delay of INIT_RETRY_OFFSETS_MS) {
      const id = window.setTimeout(() => {
        if (ackReceived) return
        sendInit()
      }, delay)
      retryTimers.push(id)
    }
  }

  function onLoad() {
    sendInit()
    scheduleInitRetries()
  }

  async function handleTokenExpired() {
    try {
      const newToken = await refreshAccessToken()
      postToIframe({ type: 'helm:token:refreshed', payload: { token: newToken } })
    } catch {
      // refreshAccessToken already redirected to /login on failure.
    }
  }

  function handleMessage(event: MessageEvent) {
    const data = event.data as { type?: string; payload?: Record<string, unknown> }
    if (!data?.type) return

    // Any message from the plugin proves its listener is up — no need to
    // keep retrying init.
    if (event.source && event.source === iframeRef.value?.contentWindow) {
      ackReceived = true
    }

    if (data.type === 'helm:ready') {
      sendInit()
    } else if (data.type === 'helm:navigate' && data.payload?.route) {
      router.push({ name: data.payload.route as string })
    } else if (data.type === 'helm:token:expired') {
      handleTokenExpired()
    }
  }

  let stopTokenListener: (() => void) | null = null

  onMounted(() => {
    window.addEventListener('message', handleMessage)
    // When the parent's axios interceptor refreshes the token (e.g. main app
    // call returned 401), push the new token to every live iframe.
    stopTokenListener = onAccessTokenRefreshed((token) => {
      postToIframe({ type: 'helm:token:refreshed', payload: { token } })
    })
  })

  onUnmounted(() => {
    window.removeEventListener('message', handleMessage)
    clearRetries()
    stopTokenListener?.()
    stopTokenListener = null
  })

  return { onLoad }
}
