<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import HelmLoader from '@/components/HelmLoader.vue'

const PENDING_KEY = 'helm:pending-redirect'

const router = useRouter()
const auth = useAuthStore()

const state = ref<'loading' | 'success' | 'error' | 'need-login'>('loading')
const errorMsg = ref('')

onMounted(async () => {
  // Extract token from path: /setup/superuser/<token>
  const token = window.location.pathname.split('/').pop() ?? ''

  if (!auth.isLoggedIn) {
    // Save this URL so AuthCallbackView can redirect back after login
    sessionStorage.setItem(PENDING_KEY, window.location.pathname)
    state.value = 'need-login'
    return
  }

  try {
    const { data } = await api.get(`/api/v1/setup/superuser/${token}`)
    auth.setTokens(data)
    state.value = 'success'
    setTimeout(() => router.replace('/dashboard'), 1800)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? '请求失败，请重试'
    state.value = 'error'
  }
})

function goLogin() {
  auth.loginWithEve()
}
</script>

<template>
  <div class="setup-container">
    <template v-if="state === 'loading'">
      <HelmLoader :size="72" color="#c96442" caption="正在授权超级管理员权限…" overlay />
    </template>

    <template v-else-if="state === 'need-login'">
      <div class="icon">🔑</div>
      <p class="title">需要先登录</p>
      <p class="hint">请通过 EVE SSO 登录，登录完成后将自动返回此页面完成授权。</p>
      <button class="btn" @click="goLogin">使用 EVE Online 登录</button>
    </template>

    <template v-else-if="state === 'success'">
      <div class="icon success-icon">✓</div>
      <p class="title success">超级管理员权限已授予</p>
      <p class="hint">正在跳转到 Dashboard…</p>
    </template>

    <template v-else-if="state === 'error'">
      <div class="icon error-icon">✕</div>
      <p class="title error">授权失败</p>
      <p class="hint">{{ errorMsg }}</p>
      <a class="link" href="/login">返回登录</a>
    </template>
  </div>
</template>

<style scoped>
.setup-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #141413;
  color: #b0aea5;
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
}

.icon {
  font-size: 3rem;
  line-height: 1;
}

.success-icon { color: #c96442; }
.error-icon   { color: #f85149; }

.title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
  color: #e8e6e1;
}

.title.success { color: #c96442; }
.title.error   { color: #f85149; }

.hint {
  font-size: 0.875rem;
  color: #5e5d59;
  margin: 0;
  text-align: center;
  max-width: 360px;
}

.btn {
  margin-top: 8px;
  padding: 10px 24px;
  background: #c96442;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn:hover { opacity: 0.85; }

.link {
  color: #c96442;
  font-size: 0.875rem;
  text-decoration: none;
}
.link:hover { text-decoration: underline; }
</style>
