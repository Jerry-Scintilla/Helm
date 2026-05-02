<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

interface CharacterSummary {
  character_id: number
  character_name: string
  corporation_id: number | null
  corporation_name: string | null
  alliance_id: number | null
  alliance_name: string | null
  is_primary: boolean
}

const router = useRouter()
const auth = useAuthStore()
const characters = ref<CharacterSummary[]>([])
const loading = ref(true)

async function loadCharacters() {
  try {
    const res = await api.get('/api/v1/characters/')
    characters.value = res.data
  } catch {
    // ignore
  }
}

onMounted(async () => {
  await loadCharacters()
  loading.value = false
})

function goCharacter(id: number) {
  router.push(`/character/${id}/overview`)
}

async function addCharacter() {
  try {
    const redirectUrl = await auth.bindCharacter()
    window.location.href = redirectUrl
  } catch {
    // ignore
  }
}

async function setPrimary(char: CharacterSummary) {
  await api.post(`/api/v1/characters/${char.character_id}/set-primary`)
  auth.updatePrimary(char.character_id, char.character_name)
  await loadCharacters()
}

async function unbind(char: CharacterSummary) {
  await api.delete(`/api/v1/characters/${char.character_id}`)
  await loadCharacters()
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
        :class="{ 'char-card--primary': char.is_primary }"
      >
        <div class="char-main" @click="goCharacter(char.character_id)">
          <div class="char-portrait-wrap">
            <img
              :src="`https://images.evetech.net/characters/${char.character_id}/portrait?size=128`"
              :alt="char.character_name"
              class="char-portrait"
            />
          </div>
          <div class="char-info">
            <div class="char-name-row">
              <span class="char-name">{{ char.character_name }}</span>
              <span v-if="char.is_primary" class="primary-badge">◈ 主角色</span>
            </div>
            <div class="char-meta">
              <span v-if="char.corporation_name" class="meta-tag">{{ char.corporation_name }}</span>
              <span v-else-if="char.corporation_id" class="meta-tag">Corp {{ char.corporation_id }}</span>
              <span v-if="char.alliance_name" class="meta-tag">{{ char.alliance_name }}</span>
              <span v-else-if="char.alliance_id" class="meta-tag">Alliance {{ char.alliance_id }}</span>
            </div>
          </div>
          <div class="char-arrow">→</div>
        </div>

        <div class="char-actions" v-if="characters.length > 1 || !char.is_primary">
          <button
            v-if="!char.is_primary"
            class="action-btn action-btn--primary"
            @click.stop="setPrimary(char)"
          >
            设为主角色
          </button>
          <button
            v-if="!char.is_primary"
            class="action-btn action-btn--danger"
            @click.stop="unbind(char)"
          >
            解绑
          </button>
        </div>
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
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.18s, background 0.18s;
}
.char-card:hover {
  border-color: #c96442;
  background: #252523;
}
.char-card--primary {
  border-color: #c96442;
}
.char-main {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  cursor: pointer;
}
.char-portrait-wrap {
  flex-shrink: 0;
}
.char-portrait {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  border: 1px solid #30302e;
  display: block;
}
.char-info {
  flex: 1;
  min-width: 0;
}
.char-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.char-name {
  font-size: 1rem;
  font-weight: 500;
  color: #faf9f5;
}
.primary-badge {
  font-size: 0.72rem;
  color: #c96442;
  background: rgba(201, 100, 66, 0.12);
  border: 1px solid rgba(201, 100, 66, 0.3);
  padding: 1px 7px;
  border-radius: 4px;
  white-space: nowrap;
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
.char-actions {
  display: flex;
  gap: 8px;
  padding: 8px 20px 12px;
  border-top: 1px solid #2a2a28;
}
.action-btn {
  font-size: 0.78rem;
  padding: 3px 12px;
  border-radius: 4px;
  border: 1px solid transparent;
  cursor: pointer;
  background: transparent;
  transition: color 0.15s, border-color 0.15s;
}
.action-btn--primary {
  color: #87867f;
  border-color: #30302e;
}
.action-btn--primary:hover {
  color: #c96442;
  border-color: #c96442;
}
.action-btn--danger {
  color: #5e5d59;
  border-color: #30302e;
}
.action-btn--danger:hover {
  color: #b53333;
  border-color: #b53333;
}
</style>
