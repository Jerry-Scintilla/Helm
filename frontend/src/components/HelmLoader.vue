<script setup lang="ts">
// Motion 03 · Reveal — the standard Helm loading state.
// Outer ring → inner ring → 8 spokes stroke in sequence, then reverse, loop.
// Use `overlay` for a full-screen centered container (e.g. auth callback, page transitions).
// Without `overlay` it renders inline at the given size.
import HelmWheel from './HelmWheel.vue'

withDefaults(defineProps<{
  size?: number
  color?: string
  caption?: string
  overlay?: boolean
}>(), {
  size: 64,
  color: '#c96442',
  caption: '',
  overlay: false,
})
</script>

<template>
  <div :class="['helm-loader', { 'helm-loader--overlay': overlay }]">
    <HelmWheel :size="size" :color="color" variant="drawIn" />
    <div v-if="caption" class="helm-loader__caption">
      {{ caption }}
      <span class="helm-loader__dots" aria-hidden="true">
        <i /><i /><i />
      </span>
    </div>
  </div>
</template>

<style scoped>
.helm-loader {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.helm-loader--overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #141413;
  z-index: 9999;
}

.helm-loader__caption {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #87867f;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.helm-loader__dots {
  display: inline-flex;
  gap: 3px;
}

.helm-loader__dots i {
  display: inline-block;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #c96442;
  animation: helm-blink 0.9s steps(1) infinite;
}
.helm-loader__dots i:nth-child(2) { animation-delay: 0.15s; }
.helm-loader__dots i:nth-child(3) { animation-delay: 0.30s; }

@keyframes helm-blink {
  0%, 49%  { opacity: 1;   }
  50%, 100%{ opacity: 0.2; }
}

@media (prefers-reduced-motion: reduce) {
  .helm-loader__dots i { animation: none; opacity: 1; }
}
</style>
