<template>
  <iframe
    ref="iframeRef"
    :src="iframeSrc"
    class="plugin-iframe"
    sandbox="allow-scripts allow-same-origin allow-forms"
    @load="onLoad"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { usePluginStore } from '@/stores/plugin'
import { useLocaleStore } from '@/stores/locale'
import { useIframePluginHost } from '@/composables/useIframePluginHost'

const route = useRoute()
const pluginStore = usePluginStore()
const localeStore = useLocaleStore()
const iframeRef = ref<HTMLIFrameElement>()
const mountToken = Date.now()

const { onLoad } = useIframePluginHost(iframeRef)

const iframeSrc = computed(() => {
  const base = route.meta.frontendUrl as string | undefined
  if (!base) return 'about:blank'
  const pluginName = route.meta.pluginName as string | undefined
  const token = pluginName ? pluginStore.pluginCacheTokens[pluginName] : undefined
  const lang = localeStore.locale
  const sep = base.includes('?') ? '&' : '?'
  return `${base}${sep}_v=${token ?? mountToken}&lang=${lang}`
})

onMounted(() => {
  const pluginName = route.meta.pluginName as string | undefined
  if (pluginName) pluginStore.ensureCacheToken(pluginName)
})
</script>

<style scoped>
.plugin-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}
</style>
