<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

interface Character {
  character_id: number
  character_name: string
  corporation_id: number | null
  alliance_id: number | null
}

const router = useRouter()
const auth = useAuthStore()
const characters = ref<Character[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/api/v1/characters/')
    characters.value = res.data
  } catch {
    // Permission error or unauthenticated
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard">
    <header class="topbar">
      <span class="brand">Helm</span>
      <div class="user-info">
        <span>{{ auth.characterName }}</span>
        <button @click="auth.logout().then(() => router.push('/login'))">退出</button>
      </div>
    </header>

    <main class="content">
      <h2>我的角色</h2>
      <div v-if="loading" class="muted">加载中...</div>
      <div v-else-if="characters.length === 0" class="muted">
        暂无已绑定角色。请通过 EVE SSO 登录以绑定角色。
      </div>
      <div v-else class="character-list">
        <div
          v-for="char in characters"
          :key="char.character_id"
          class="character-card"
          @click="router.push(`/character/${char.character_id}/overview`)"
        >
          <img
            :src="`https://images.evetech.net/characters/${char.character_id}/portrait?size=64`"
            :alt="char.character_name"
            class="avatar"
          />
          <div>
            <div class="char-name">{{ char.character_name }}</div>
            <div class="char-meta">Corp ID: {{ char.corporation_id ?? '—' }}</div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard { min-height: 100vh; background: #0d1117; color: #c9d1d9; }
.topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 24px; background: #161b22; border-bottom: 1px solid #30363d;
}
.brand { font-size: 1.2rem; letter-spacing: 3px; color: #58a6ff; }
.user-info { display: flex; gap: 16px; align-items: center; }
.user-info button {
  background: none; border: 1px solid #30363d; color: #8b949e;
  padding: 4px 12px; border-radius: 6px; cursor: pointer;
}
.content { max-width: 960px; margin: 0 auto; padding: 32px 24px; }
h2 { color: #c9d1d9; margin-bottom: 24px; }
.muted { color: #8b949e; }
.character-list { display: flex; flex-wrap: wrap; gap: 16px; }
.character-card {
  display: flex; align-items: center; gap: 16px;
  padding: 16px 20px; background: #161b22; border-radius: 8px;
  border: 1px solid #30363d; cursor: pointer; transition: border-color 0.2s;
  min-width: 240px;
}
.character-card:hover { border-color: #58a6ff; }
.avatar { width: 48px; height: 48px; border-radius: 50%; }
.char-name { font-weight: 600; }
.char-meta { font-size: 0.85rem; color: #8b949e; margin-top: 4px; }
</style>
