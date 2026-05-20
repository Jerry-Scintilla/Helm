<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import HelmLoader from '@/components/HelmLoader.vue'

const router = useRouter()
const auth = useAuthStore()
const error = ref<string | null>(null)
const bindSuccess = ref<string | null>(null)

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

    if (data.type === 'bind') {
      bindSuccess.value = `角色 ${data.character_name} 已成功绑定`
      setTimeout(() => router.replace('/dashboard'), 1500)
    } else {
      auth.setTokens(data)
      router.replace('/dashboard')
    }
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
    <template v-else-if="bindSuccess">
      <p class="success">{{ bindSuccess }}</p>
      <p class="hint">正在返回 Dashboard...</p>
    </template>
    <template v-else>
      <HelmLoader :size="72" color="#c96442" caption="正在处理登录" overlay />
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
  background: #141413;
  color: #b0aea5;
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
}

.error {
  color: #f85149;
}

.success {
  color: #c96442;
  font-weight: 500;
}

.hint {
  font-size: 0.875rem;
  color: #5e5d59;
}
</style>
