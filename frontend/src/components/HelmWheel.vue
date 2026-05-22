<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: number
  color?: string
  // auto = pick variant by size; full/mid/tiny = force detail level
  // drawIn = Motion 03 Reveal; pulse = Status pip; spinning = continuous rotation
  variant?: 'auto' | 'full' | 'mid' | 'tiny' | 'drawIn' | 'pulse' | 'spinning'
}>(), {
  size: 64,
  color: '#c96442',
  variant: 'auto',
})

const resolved = computed(() => {
  if (props.variant !== 'auto') return props.variant
  if (props.size <= 20) return 'tiny'
  if (props.size <= 36) return 'mid'
  return 'full'
})

// Full-detail spokes: inner r=12 → outer r=44
const spokesFullRaw = Array.from({ length: 8 }, (_, i) => {
  const a = (i * 45) * Math.PI / 180
  return {
    x1: 50 + Math.cos(a) * 12, y1: 50 + Math.sin(a) * 12,
    x2: 50 + Math.cos(a) * 44, y2: 50 + Math.sin(a) * 44,
    delay: `${0.2 + i * 0.03}s`,
  }
})

// Mid-detail spokes: inner r=15 → outer r=45 (no inner ring)
const spokesMidRaw = Array.from({ length: 8 }, (_, i) => {
  const a = (i * 45) * Math.PI / 180
  return {
    x1: 50 + Math.cos(a) * 15, y1: 50 + Math.sin(a) * 15,
    x2: 50 + Math.cos(a) * 45, y2: 50 + Math.sin(a) * 45,
  }
})

// Tiny spokes: 4 only, inner r=14 → outer r=50
const spokesTinyRaw = Array.from({ length: 4 }, (_, i) => {
  const a = (i * 90) * Math.PI / 180
  return {
    x1: 50 + Math.cos(a) * 14, y1: 50 + Math.sin(a) * 14,
    x2: 50 + Math.cos(a) * 50, y2: 50 + Math.sin(a) * 50,
  }
})
</script>

<template>
  <!-- ── full (48px+): outer ring + inner ring + 8 spokes ── -->
  <svg
    v-if="resolved === 'full'"
    :width="size" :height="size"
    viewBox="0 0 100 100" fill="none"
    :stroke="color" stroke-width="3.2" stroke-linecap="round"
    style="display:block;flex-shrink:0"
  >
    <circle cx="50" cy="50" r="32"/>
    <circle cx="50" cy="50" r="9"/>
    <line v-for="(s, i) in spokesFullRaw" :key="i"
      :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2"/>
    <circle cx="50" cy="50" r="2.2" :fill="color" stroke="none"/>
  </svg>

  <!-- ── mid (24–36px): outer ring + 8 spokes, thicker strokes ── -->
  <svg
    v-else-if="resolved === 'mid'"
    :width="size" :height="size"
    viewBox="0 0 100 100" fill="none"
    :stroke="color" stroke-width="6" stroke-linecap="round"
    style="display:block;flex-shrink:0"
  >
    <circle cx="50" cy="50" r="30"/>
    <line v-for="(s, i) in spokesMidRaw" :key="i"
      :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2"/>
    <circle cx="50" cy="50" r="5" :fill="color" stroke="none"/>
  </svg>

  <!-- ── tiny (≤20px): outer ring + 4 spokes, very thick strokes ── -->
  <svg
    v-else-if="resolved === 'tiny'"
    :width="size" :height="size"
    viewBox="0 0 100 100" fill="none"
    :stroke="color" stroke-width="10" stroke-linecap="round"
    style="display:block;flex-shrink:0"
  >
    <circle cx="50" cy="50" r="28"/>
    <line v-for="(s, i) in spokesTinyRaw" :key="i"
      :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2"/>
    <circle cx="50" cy="50" r="9" :fill="color" stroke="none"/>
  </svg>

  <!-- ── spinning: full-detail wheel, continuous rotation ── -->
  <svg
    v-else-if="resolved === 'spinning'"
    :width="size" :height="size"
    viewBox="0 0 100 100" fill="none"
    :stroke="color" stroke-width="3.2" stroke-linecap="round"
    class="helm-spin"
    style="display:block;flex-shrink:0;transform-origin:50% 50%"
  >
    <circle cx="50" cy="50" r="32"/>
    <circle cx="50" cy="50" r="9"/>
    <line v-for="(s, i) in spokesFullRaw" :key="i"
      :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2"/>
    <circle cx="50" cy="50" r="2.2" :fill="color" stroke="none"/>
  </svg>

  <!-- ── drawIn: Motion 03 · Reveal — ring then spokes stroke in ── -->
  <svg
    v-else-if="resolved === 'drawIn'"
    :width="size" :height="size"
    viewBox="0 0 100 100" fill="none"
    :stroke="color" stroke-width="3.2" stroke-linecap="round"
    style="display:block;flex-shrink:0"
  >
    <circle cx="50" cy="50" r="32" class="helm-draw-ring" pathLength="220"/>
    <circle cx="50" cy="50" r="9"  class="helm-draw-ring" pathLength="220" style="animation-delay:0.1s"/>
    <line
      v-for="(s, i) in spokesFullRaw" :key="i"
      :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2"
      class="helm-draw-spoke" pathLength="60"
      :style="`animation-delay:${s.delay}`"
    />
    <circle cx="50" cy="50" r="2.2" :fill="color" stroke="none"/>
  </svg>

  <!-- ── pulse: static wheel, pulsing center pip ── -->
  <svg
    v-else-if="resolved === 'pulse'"
    :width="size" :height="size"
    viewBox="0 0 100 100" fill="none"
    :stroke="color" stroke-width="3.2" stroke-linecap="round"
    style="display:block;flex-shrink:0"
  >
    <circle cx="50" cy="50" r="32"/>
    <circle cx="50" cy="50" r="9"/>
    <line v-for="(s, i) in spokesFullRaw" :key="i"
      :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2"/>
    <circle cx="50" cy="50" r="3.5" fill="#c96442" stroke="none"
      class="helm-pip-pulse"
      style="transform-origin:50% 50%;transform-box:fill-box"/>
  </svg>
</template>

<style>
/* Shared keyframes — global so HelmLoader can reference them too */
@keyframes helm-spin-fast {
  to { transform: rotate(360deg); }
}
@keyframes helm-draw-ring-kf {
  from { stroke-dashoffset: 220; opacity: 0.3; }
  to   { stroke-dashoffset: 0;   opacity: 1;   }
}
@keyframes helm-draw-spoke-kf {
  from { stroke-dashoffset: 60; }
  to   { stroke-dashoffset: 0;  }
}
@keyframes helm-pip-pulse-kf {
  0%, 100% { opacity: 1; transform: scale(1);    }
  50%       { opacity: 0.3; transform: scale(0.85); }
}
@keyframes helm-rotate-snap {
  0%   { transform: rotate(-60deg); opacity: 0; }
  60%  { transform: rotate(8deg);   opacity: 1; }
  80%  { transform: rotate(-3deg); }
  100% { transform: rotate(0deg); }
}
@keyframes helm-letter-in {
  from { opacity: 0; transform: translateY(6px); filter: blur(2px); }
  to   { opacity: 1; transform: translateY(0);   filter: blur(0);   }
}
@keyframes helm-blink {
  0%, 49%  { opacity: 1;   }
  50%, 100%{ opacity: 0.2; }
}
</style>

<style scoped>
.helm-spin {
  animation: helm-spin-fast 1.6s linear infinite;
}

.helm-draw-ring {
  stroke-dasharray: 220;
  stroke-dashoffset: 220;
  animation: helm-draw-ring-kf 0.8s ease-out forwards infinite;
  animation-direction: alternate;
}

.helm-draw-spoke {
  stroke-dasharray: 60;
  stroke-dashoffset: 60;
  animation: helm-draw-spoke-kf 0.7s ease-out forwards infinite;
  animation-direction: alternate;
}

.helm-pip-pulse {
  animation: helm-pip-pulse-kf 2.4s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .helm-spin,
  .helm-draw-ring,
  .helm-draw-spoke { animation: none; }
  .helm-draw-ring  { stroke-dashoffset: 0; opacity: 1; }
  .helm-draw-spoke { stroke-dashoffset: 0; }
}
</style>
