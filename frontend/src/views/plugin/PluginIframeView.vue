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

const route = useRoute()
const router = useRouter()
const iframeRef = ref<HTMLIFrameElement>()

const iframeSrc = computed(() => route.meta.frontendUrl as string)
const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function sendInit() {
  iframeRef.value?.contentWindow?.postMessage(
    {
      type: 'helm:init',
      payload: {
        token: localStorage.getItem('access_token'),
        apiBase,
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
