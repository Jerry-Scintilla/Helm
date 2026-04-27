<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

interface CharacterSummary {
  character_id: number
  character_name: string
  corporation_id: number | null
  alliance_id: number | null
}

const router = useRouter()
const characters = ref<CharacterSummary[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/api/v1/characters/')
    characters.value = res.data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})

function goCharacter(id: number) {
  router.push(`/character/${id}/overview`)
}

function addCharacter() {
  const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
  window.location.href = `${base}/auth/eve/login`
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title h-serif">Dashboard</h1>
      <n-button size="small" type="primary" @click="addCharacter">+ 添加角色</n-button>
    </div>

    <n-spin v-if="loading" :size="24" class="spinner" />

    <div v-else-if="characters.length === 0" class="empty-state">
      <div class="empty-icon">◈</div>
      <p class="empty-title">尚无已绑定角色</p>
      <p class="empty-sub">通过 EVE SSO 登录以绑定你的 EVE Online 角色</p>
      <n-button type="primary" style="margin-top:16px" @click="addCharacter">绑定 EVE 角色</n-button>
    </div>

    <div v-else class="character-grid">
      <div
        v-for="char in characters"
        :key="char.character_id"
        class="char-card"
        @click="goCharacter(char.character_id)"
      >
        <img
          :src="`https://images.evetech.net/characters/${char.character_id}/portrait?size=128`"
          :alt="char.character_name"
          class="char-portrait"
        />
        <div class="char-info">
          <div class="char-name">{{ char.character_name }}</div>
          <div class="char-meta">
            <span v-if="char.corporation_id" class="meta-tag">
              Corp {{ char.corporation_id }}
            </span>
            <span v-if="char.alliance_id" class="meta-tag">
              Alliance {{ char.alliance_id }}
            </span>
          </div>
        </div>
        <div class="char-arrow">→</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 28px;
}
.page-title {
  font-size: 1.8rem;
  color: #faf9f5;
  font-weight: 500;
  line-height: 1.2;
}
.spinner {
  display: block;
  margin: 60px auto;
}
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #87867f;
}
.empty-icon {
  font-size: 3rem;
  color: #30302e;
  margin-bottom: 16px;
}
.empty-title {
  font-size: 1.1rem;
  color: #b0aea5;
  margin-bottom: 8px;
}
.empty-sub {
  font-size: 0.9rem;
}
.character-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.char-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s;
}
.char-card:hover {
  border-color: #c96442;
  background: #252523;
}
.char-portrait {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  border: 1px solid #30302e;
  flex-shrink: 0;
}
.char-info {
  flex: 1;
  min-width: 0;
}
.char-name {
  font-size: 1rem;
  font-weight: 500;
  color: #faf9f5;
  margin-bottom: 6px;
}
.char-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.meta-tag {
  font-size: 0.78rem;
  color: #87867f;
  background: #30302e;
  padding: 2px 8px;
  border-radius: 4px;
}
.char-arrow {
  color: #5e5d59;
  font-size: 1rem;
}
</style>
