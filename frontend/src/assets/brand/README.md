# Helm Brand Assets

Logo and motion resources from the Claude Design handoff (`Helm Favicon & Motion`).
This directory is a **resource library** — nothing here is auto-wired into the app.
Import what you need when you need it.

## Quick start

```ts
import { brand, brandColors, brandMotion } from '@/assets/brand'

// In a template
// <img :src="brand.lockup.horizontal.ivory" alt="Helm" />
// <img :src="brand.wheel.full.terracotta" />

// Tokens
// background: brandColors.nearBlack
// animation: `${brandMotion.spinFast.duration} ${brandMotion.spinFast.easing}
//             infinite ${brandMotion.spinFast.name}`
```

All asset values are Vite-resolved URL strings (hashed at build time, lazy-
loaded). The runtime spinner / draw-in / pulse animations live in
[`components/HelmWheel.vue`](../../components/HelmWheel.vue) — `brandMotion`
just mirrors its timing tokens so bespoke animations stay in sync.

## Directory layout

```
brand/
├── index.ts        — typed index (default + named exports)
├── README.md       — this file
├── svg/            — vector masters, prefer these
├── png/            — rasters (favicons / app store / canvas)
├── motion/         — standalone @keyframes + utility classes
│   └── helm-motion.css
└── source/         — original Claude Design handoff (HTML + JSX)
                     archival only — not bundled
```

## When to use which mark

| Mark | When |
|------|------|
| `wheel.full.*` | ≥48 px. 8 spokes + inner ring. Default in-app brand mark. |
| `wheel.mid.*` | 24–36 px. 8 spokes, no inner ring, thicker strokes. |
| `wheel.tiny.*` | ≤20 px. 4 spokes only, fat strokes. Favicons / dense menus. |
| `appIcon.*` | Pre-composed squircle for app stores / install banners. |
| `hMark.*` | Serif "H." monogram — wordmark direction favicon ≥24 px. |
| `lockup.horizontal.*` | Wheel + "Helm." inline. Headers, login splash, marketing. |

Colors:

| Token | Hex | Use |
|-------|-----|-----|
| `black` | `#141413` | On light surfaces |
| `ivory` | `#faf9f5` | On dark surfaces |
| `terracotta` | `#c96442` | Primary brand |
| `coral` | `#d97757` | Hover / highlight variant |

## Motion catalogue

The four loops from the design's *Motion studies* are already implemented as
`variant` props on `HelmWheel`:

| Design label | `variant` | Use |
|---|---|---|
| 01 · Idle | `spinning` (24s via custom CSS) | Hero, splash, dark banner |
| 02 · Loading | `spinning` (1.6s default) | ESI sync, async data loads |
| 03 · Reveal | `drawIn` | First-paint / page-mount entrance |
| 04 · Pulse | `pulse` | "Connected / live" indicator |

For one-off animations outside `HelmWheel`, two equivalent paths:

**A. Utility class** — pull in the stylesheet once, drop the class on any element:

```css
/* in some component or main.css */
@import '@/assets/brand/motion/helm-motion.css';
```

```html
<svg class="helm-anim-spin">...</svg>
<span class="helm-anim-blink">.</span>
```

Available classes: `helm-anim-spin` (1.6s · Loading), `helm-anim-spin-slow`
(24s · Idle), `helm-anim-rotate-snap` (entrance), `helm-anim-letter-in`,
`helm-anim-blink`, `helm-anim-stop-pulse`, `helm-anim-pip-pulse`.

**B. Token-driven** — when you need to compose your own animation shorthand:

```ts
import { brandMotion } from '@/assets/brand'
const m = brandMotion.spinFast
// style: `animation: ${m.name} ${m.duration} ${m.easing} infinite`
```

The CSS file also handles `prefers-reduced-motion: reduce` (disables all
`helm-anim-*` rotations) so you don't need to add that yourself.

## Adding new assets

Put new SVG/PNG files under `svg/` or `png/`, then add a corresponding entry
to `index.ts` so consumers get type-checked access. Don't import raw paths
elsewhere in the codebase — go through `brand.*` so renames stay safe.

## Source

Generated from `Helm Favicon & Motion.html` (Claude Design handoff).
To re-render variants at custom sizes, edit `wheel-variants.jsx` in the
original design bundle and re-export.
