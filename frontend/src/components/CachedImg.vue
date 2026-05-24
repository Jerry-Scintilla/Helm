<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { getCachedImageUrl } from '@/utils/imageCache'
import HelmWheel from '@/components/HelmWheel.vue'

// Drop-in <img> replacement that resolves `src` via the IndexedDB image
// cache. While the cached blob is being looked up / fetched the original src
// is used so the browser starts loading immediately; once the cached object
// URL resolves we swap it in. If both cache and the network <img> load fail,
// we fall back to the Helm wheel spinner (Motion 02 · Loading from the
// design system) so users see a recognizable placeholder instead of the
// browser's broken-image glyph.

const props = withDefaults(
  defineProps<{
    src: string | null | undefined
    alt?: string
    width?: number | string
    height?: number | string
    loading?: 'lazy' | 'eager' | 'auto'
  }>(),
  { alt: '', loading: 'lazy' },
)

const emit = defineEmits<{ error: [Event]; load: [Event] }>()

const resolvedSrc = ref<string>('')
const failed = ref(false)

watch(
  () => props.src,
  async (url) => {
    failed.value = false
    if (!url) {
      resolvedSrc.value = ''
      return
    }
    // Show original URL immediately; if cache returns a different value
    // (object URL) we swap in.
    resolvedSrc.value = url
    try {
      const cached = await getCachedImageUrl(url)
      if (props.src === url) resolvedSrc.value = cached
    } catch {
      // keep the original URL — browser <img> will attempt and either
      // succeed or trigger onError below.
    }
  },
  { immediate: true },
)

// Pixel size for the fallback spinner. Prefer width, then height, then a
// reasonable default. Clamped so it still reads at small icon sizes.
const fallbackSize = computed(() => {
  const raw = props.width ?? props.height
  const n = typeof raw === 'number' ? raw : Number(raw)
  if (Number.isFinite(n) && n > 0) return Math.max(12, Math.round(n))
  return 24
})

function onImgError(e: Event) {
  failed.value = true
  emit('error', e)
}
</script>

<template>
  <span
    v-if="failed"
    class="cached-img-fallback"
    :style="{ width: fallbackSize + 'px', height: fallbackSize + 'px' }"
    role="img"
    :aria-label="alt || 'image unavailable'"
  >
    <HelmWheel :size="fallbackSize" variant="spinning" />
  </span>
  <img
    v-else-if="resolvedSrc"
    :src="resolvedSrc"
    :alt="alt"
    :width="width"
    :height="height"
    :loading="loading"
    @error="onImgError"
    @load="(e) => emit('load', e)"
  />
</template>

<style scoped>
.cached-img-fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
