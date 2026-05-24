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
  const pluginName = route.meta.pluginName as string
  const slug = route.meta.submoduleSlug as string
  const cid = route.params.id as string
  const plugin = pluginStore.plugins.find(p => p.name === pluginName)
  const sub = plugin?.meta?.character_submodules?.find(s => s.slug === slug)
  const base = sub?.iframe_url_template?.replace('{character_id}', cid) ?? ''
  if (!base) return 'about:blank'
  const token = pluginStore.pluginCacheTokens[pluginName] ?? mountToken
  const lang = localeStore.locale
  const sep = base.includes('?') ? '&' : '?'
  return `${base}${sep}_v=${token}&lang=${lang}`
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
