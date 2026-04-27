<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

onMounted(async () => {
  // The EVE SSO callback goes to the backend; the backend returns JSON.
  // But if the user is redirected back to the frontend with tokens in the URL hash
  // (future: set cookies from backend), handle it here.
  // For now, the backend /auth/eve/callback returns JSON directly.
  // In production, use HttpOnly cookies instead.
  const params = new URLSearchParams(window.location.search)
  const code = params.get('code')
  if (code) {
    // If backend redirects here after SSO, handle token extraction
    // For current setup, backend returns JSON at /auth/eve/callback
    // and the frontend doesn't receive a redirect — just navigate home
  }
  if (auth.isLoggedIn) {
    router.replace('/dashboard')
  } else {
    router.replace('/login')
  }
})
</script>

<template>
  <div class="callback-loading">
    <p>正在处理登录...</p>
  </div>
</template>

<style scoped>
.callback-loading {
  display: flex;
  height: 100vh;
  align-items: center;
  justify-content: center;
  color: #8b949e;
}
</style>
