// Helm brand asset index — typed access to the Logo & Motion design bundle.
//
// Usage:
//   import { brand } from '@/assets/brand'
//   <img :src="brand.wheel.full.black" />
//   <img :src="brand.lockup.horizontal.ivory" />
//
// Each value is a Vite-resolved URL string (works in <img :src>, CSS
// background-image, fetch(), etc.). SVG masters are preferred for in-app use;
// PNG rasters are kept for places that need a fixed bitmap (export, email,
// canvas drawing).
//
// See README.md in this directory for the design rationale and size guidance.

// ── SVG vector masters ──────────────────────────────────────────────────────
import wheelFullBlack from './svg/wheel-full-black.svg?url'
import wheelFullIvory from './svg/wheel-full-ivory.svg?url'
import wheelFullTerracotta from './svg/wheel-full-terracotta.svg?url'
import wheelFullCoral from './svg/wheel-full-coral.svg?url'
import wheelMidBlack from './svg/wheel-mid-black.svg?url'
import wheelMidIvory from './svg/wheel-mid-ivory.svg?url'
import wheelTinyBlack from './svg/wheel-tiny-black.svg?url'
import wheelTinyIvory from './svg/wheel-tiny-ivory.svg?url'

import appIconBlack from './svg/app-icon-black.svg?url'
import appIconIvory from './svg/app-icon-ivory.svg?url'
import appIconTerracotta from './svg/app-icon-terracotta.svg?url'

import hMarkBlack from './svg/h-mark-black.svg?url'
import hMarkIvory from './svg/h-mark-ivory.svg?url'

import lockupHorizontalBlack from './svg/lockup-horizontal-black.svg?url'
import lockupHorizontalIvory from './svg/lockup-horizontal-ivory.svg?url'

// ── PNG rasters ─────────────────────────────────────────────────────────────
import favicon16 from './png/favicon-16.png?url'
import favicon32 from './png/favicon-32.png?url'
import favicon48 from './png/favicon-48.png?url'
import favicon64 from './png/favicon-64.png?url'
import favicon128 from './png/favicon-128.png?url'
import favicon192 from './png/favicon-192.png?url'
import favicon256 from './png/favicon-256.png?url'
import favicon512 from './png/favicon-512.png?url'

import appleTouchIcon180 from './png/apple-touch-icon-180.png?url'
import androidChrome192 from './png/android-chrome-192.png?url'
import androidChrome512 from './png/android-chrome-512.png?url'
import androidChrome192Dark from './png/android-chrome-192-dark.png?url'
import androidChrome512Dark from './png/android-chrome-512-dark.png?url'

// ── Tokens (matches design system) ──────────────────────────────────────────
export const brandColors = {
  parchment: '#f5f4ed',
  ivory: '#faf9f5',
  terracotta: '#c96442',
  coral: '#d97757',
  nearBlack: '#141413',
  darkSurface: '#30302e',
  warmSilver: '#b0aea5',
  borderCream: '#f0eee6',
  borderWarm: '#e8e6dc',
  olive: '#5e5d59',
  stone: '#87867f',
} as const

// ── Motion tokens (matches HelmWheel keyframes) ─────────────────────────────
// All durations & easings live in HelmWheel.vue's <style>; mirrored here so
// callers building bespoke animations stay in sync with the design.
export const brandMotion = {
  // 02 · Loading — the workhorse spinner.
  spinFast: { duration: '1.6s', easing: 'linear', name: 'helm-spin-fast' },
  // 01 · Idle — barely-perceptible rotation for hero / dark banners.
  spinSlow: { duration: '24s', easing: 'linear', name: 'helm-spin-fast' },
  // 03 · Reveal — outer ring → inner ring → spokes draw in.
  drawIn: { duration: '0.8s', easing: 'ease-out', name: 'helm-draw-ring-kf' },
  // 04 · Pulse — center pip breathes.
  pipPulse: { duration: '2.4s', easing: 'ease-in-out', name: 'helm-pip-pulse-kf' },
  // Combined entrance — snap-rotate from -60° with overshoot.
  rotateSnap: { duration: '1.2s', easing: 'cubic-bezier(.34,1.56,.64,1)', name: 'helm-rotate-snap' },
  // Wordmark letter-in — fade + de-blur per glyph.
  letterIn: { duration: '0.55s', easing: 'cubic-bezier(.2,.7,.3,1)', name: 'helm-letter-in' },
  // Terminal-stop blink for the wordmark's period.
  blink: { duration: '1.1s', easing: 'steps(1)', name: 'helm-blink' },
} as const

// ── Indexed exports ─────────────────────────────────────────────────────────
export const brand = {
  wheel: {
    full: {
      black: wheelFullBlack,
      ivory: wheelFullIvory,
      terracotta: wheelFullTerracotta,
      coral: wheelFullCoral,
    },
    mid: {
      black: wheelMidBlack,
      ivory: wheelMidIvory,
    },
    tiny: {
      black: wheelTinyBlack,
      ivory: wheelTinyIvory,
    },
  },
  appIcon: {
    black: appIconBlack,
    ivory: appIconIvory,
    terracotta: appIconTerracotta,
  },
  hMark: {
    black: hMarkBlack,
    ivory: hMarkIvory,
  },
  lockup: {
    horizontal: {
      black: lockupHorizontalBlack,
      ivory: lockupHorizontalIvory,
    },
  },
  favicon: {
    png16: favicon16,
    png32: favicon32,
    png48: favicon48,
    png64: favicon64,
    png128: favicon128,
    png192: favicon192,
    png256: favicon256,
    png512: favicon512,
  },
  appleTouch: {
    png180: appleTouchIcon180,
  },
  androidChrome: {
    png192: androidChrome192,
    png512: androidChrome512,
    png192Dark: androidChrome192Dark,
    png512Dark: androidChrome512Dark,
  },
} as const

export default brand
