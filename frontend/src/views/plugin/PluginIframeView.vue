<template>
  <iframe
    ref="iframeRef"
    :src="iframeSrc"
    class="plugin-iframe"
    sandbox="allow-scripts allow-same-origin allow-forms"
    @load="sendInit"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePluginStore } from '@/stores/plugin'
import { useLocaleStore } from '@/stores/locale'

const route = useRoute()
const router = useRouter()
const pluginStore = usePluginStore()
const localeStore = useLocaleStore()
const iframeRef = ref<HTMLIFrameElement>()

const iframeSrc = computed(() => {
  const base = route.meta.frontendUrl as string
  const pluginName = route.meta.pluginName as string | undefined
  const token = pluginName ? pluginStore.pluginCacheTokens[pluginName] : undefined
  const lang = localeStore.locale
  const sep = base.includes('?') ? '&' : '?'
  const parts: string[] = []
  if (token !== undefined) parts.push(`_v=${token}`)
  parts.push(`lang=${lang}`)
  return `${base}${sep}${parts.join('&')}`
})
const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function sendInit() {
  iframeRef.value?.contentWindow?.postMessage(
    {
      type: 'helm:init',
      payload: {
        token: localStorage.getItem('access_token'),
        apiBase,
        locale: localeStore.locale,
      },
    },
    '*',
  )
}

function handleMessage(event: MessageEvent) {
  const data = event.data as { type?: string; payload?: Record<string, unknown> }
  if (!data?.type) return

  if (data.type === 'helm:ready') {
    sendInit()
  } else if (data.type === 'helm:navigate' && data.payload?.route) {
    router.push({ name: data.payload.route as string })
  } else if (data.type === 'helm:token:expired') {
    // Return whatever token is currently stored; the axios interceptor will have
    // already refreshed it if an API call triggered the 401.
    iframeRef.value?.contentWindow?.postMessage(
      {
        type: 'helm:token:refreshed',
        payload: { token: localStorage.getItem('access_token') },
      },
      '*',
    )
  }
}

onMounted(() => window.addEventListener('message', handleMessage))
onUnmounted(() => window.removeEventListener('message', handleMessage))
</script>

<style scoped>
.plugin-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}
</style>
