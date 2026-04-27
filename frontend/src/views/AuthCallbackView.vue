<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()
const error = ref<string | null>(null)

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  const code = params.get('code')
  const state = params.get('state')

  if (!code || !state) {
    error.value = '缺少必要的授权参数'
    return
  }

  try {
    const { data } = await api.get('/auth/eve/callback', { params: { code, state } })
    auth.setTokens(data)
    router.replace('/dashboard')
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? '登录失败，请重试'
  }
})
</script>

<template>
  <div class="callback-container">
    <template v-if="error">
      <p class="error">{{ error }}</p>
      <a href="/login">返回登录</a>
    </template>
    <template v-else>
      <p>正在处理登录...</p>
    </template>
  </div>
</template>

<style scoped>
.callback-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #8b949e;
}

.error {
  color: #f85149;
}
</style>
