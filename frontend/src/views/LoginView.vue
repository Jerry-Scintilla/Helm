<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { t } = useI18n()

// Re-trigger the entrance animation every 4.2 s (matches the handoff CombinedLoop)
const animKey = ref(0)
let timer: ReturnType<typeof setInterval> | null = null
onMounted(() => { timer = setInterval(() => { animKey.value++ }, 4200) })
onBeforeUnmount(() => { if (timer) clearInterval(timer) })

const letters = ['H', 'e', 'l', 'm']
</script>

<template>
  <div class="login-page">
    <div class="login-card">

      <!-- Combined entrance lockup: wheel snap + letter-in -->
      <div class="brand-lockup" :key="animKey">
        <!-- Wheel: rotate-snap entrance -->
        <div class="brand-wheel-wrap">
          <svg width="48" height="48" viewBox="0 0 100 100"
               fill="none" stroke="#c96442" stroke-width="3.2" stroke-linecap="round">
            <circle cx="50" cy="50" r="32"/>
            <circle cx="50" cy="50" r="9"/>
            <line v-for="i in 8" :key="i"
              :x1="50 + Math.cos((i-1)*45*Math.PI/180)*12"
              :y1="50 + Math.sin((i-1)*45*Math.PI/180)*12"
              :x2="50 + Math.cos((i-1)*45*Math.PI/180)*44"
              :y2="50 + Math.sin((i-1)*45*Math.PI/180)*44"
            />
            <circle cx="50" cy="50" r="2.2" fill="#c96442" stroke="none"/>
          </svg>
        </div>

        <!-- Wordmark: letters fade-up in sequence -->
        <div class="brand-wordmark">
          <span
            v-for="(ch, i) in letters" :key="i"
            class="brand-letter"
            :style="`animation-delay:${0.6 + i * 0.12}s`"
          >{{ ch }}</span>
          <span
            class="brand-letter brand-stop"
            style="animation-delay:1.2s;animation-name:helm-letter-in,helm-blink;animation-duration:.55s,1.1s;animation-timing-function:cubic-bezier(.2,.7,.3,1),steps(1);animation-delay:1.2s,2s;animation-fill-mode:forwards,none;animation-iteration-count:1,infinite"
          >.</span>
        </div>
      </div>

      <p class="subtitle">{{ t('login.subtitle') }}</p>
      <div class="divider" />
      <p class="desc">{{ t('login.desc') }}</p>
      <button class="eve-btn" @click="auth.loginWithEve()">
        <img
          src="https://web.ccpgamescdn.com/eveonlineassets/developers/eve-sso-login-black-small.png"
          alt="Login with EVE Online"
        />
      </button>
      <p class="fine-print">{{ t('login.finePrint') }}</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #141413;
}

.login-card {
  text-align: center;
  padding: 48px 56px;
  background: #1e1e1c;
  border-radius: 12px;
  border: 1px solid #30302e;
  box-shadow: rgba(0,0,0,0.2) 0px 8px 32px;
  min-width: 340px;
}

/* Combined entrance lockup */
.brand-lockup {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-bottom: 14px;
}

.brand-wheel-wrap {
  display: inline-flex;
  flex-shrink: 0;
  animation: helm-rotate-snap 1.2s cubic-bezier(.34,1.56,.64,1) both;
  transform-origin: center;
}

.brand-wordmark {
  display: inline-flex;
  align-items: baseline;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 2.2rem;
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.01em;
  color: #faf9f5;
}

.brand-letter {
  display: inline-block;
  opacity: 0;
  animation: helm-letter-in 0.55s cubic-bezier(.2,.7,.3,1) forwards;
}

.brand-stop {
  color: #c96442;
}

.subtitle {
  color: #87867f;
  font-size: 0.9rem;
  margin-bottom: 0;
}

.divider {
  width: 40px;
  height: 1px;
  background: #30302e;
  margin: 24px auto;
}

.desc {
  color: #5e5d59;
  font-size: 0.85rem;
  line-height: 1.6;
  margin-bottom: 28px;
  max-width: 260px;
  margin-left: auto;
  margin-right: auto;
}

.eve-btn {
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.88;
  transition: opacity 0.18s;
  display: block;
  margin: 0 auto 20px;
}
.eve-btn:hover { opacity: 1; }

.fine-print {
  font-size: 0.72rem;
  color: #3d3d3a;
}

/* Keyframes scoped via global block in HelmWheel.vue; duplicated here for isolation */
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

@media (prefers-reduced-motion: reduce) {
  .brand-wheel-wrap { animation: none; }
  .brand-letter     { animation: none; opacity: 1; filter: none; }
}
</style>
