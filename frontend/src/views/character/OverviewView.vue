<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCharacterStore } from '@/stores/character'

const route = useRoute()
const router = useRouter()
const charStore = useCharacterStore()

const characterId = Number(route.params.id)

onMounted(() => {
  charStore.fetchAll(characterId)
})

function formatIsk(isk: number | null) {
  if (isk === null) return '—'
  return isk.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) + ' ISK'
}

function formatSp(sp: number) {
  if (sp >= 1_000_000) return (sp / 1_000_000).toFixed(2) + ' M SP'
  if (sp >= 1_000) return (sp / 1_000).toFixed(1) + ' K SP'
  return sp + ' SP'
}

function formatDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="overview-page">
    <header class="topbar">
      <button class="back-btn" @click="router.push('/dashboard')">← 返回</button>
      <span class="brand">Helm</span>
    </header>

    <main class="content">
      <div v-if="charStore.loading" class="muted">加载中...</div>
      <div v-else-if="charStore.error" class="error">{{ charStore.error }}</div>

      <template v-else-if="charStore.characterInfo">
        <!-- Character header -->
        <div class="char-header">
          <img
            :src="`https://images.evetech.net/characters/${characterId}/portrait?size=128`"
            class="avatar"
            :alt="charStore.characterInfo.character_name"
          />
          <div>
            <h1>{{ charStore.characterInfo.character_name }}</h1>
            <div class="char-meta">
              Corp ID: {{ charStore.characterInfo.corporation_id ?? '—' }}
              <span v-if="charStore.characterInfo.alliance_id">
                · Alliance ID: {{ charStore.characterInfo.alliance_id }}
              </span>
            </div>
            <div class="char-meta">
              数据更新: {{ formatDate(charStore.characterInfo.updated_at) }}
            </div>
          </div>
        </div>

        <!-- Stats grid -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">钱包余额</div>
            <div class="stat-value">{{ formatIsk(charStore.wallet?.balance ?? null) }}</div>
            <div class="stat-updated">更新于 {{ formatDate(charStore.wallet?.updated_at ?? null) }}</div>
          </div>

          <div class="stat-card">
            <div class="stat-label">技能点</div>
            <div class="stat-value">{{ formatSp(charStore.skills?.total_sp ?? 0) }}</div>
            <div class="stat-updated">{{ charStore.skills?.skills.length ?? 0 }} 个技能</div>
          </div>
        </div>

        <!-- Skills list (top 10) -->
        <div v-if="charStore.skills && charStore.skills.skills.length > 0" class="section">
          <h3>技能列表（前 10）</h3>
          <table class="skills-table">
            <thead>
              <tr>
                <th>Skill ID</th>
                <th>等级</th>
                <th>技能点</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="skill in charStore.skills.skills.slice(0, 10)" :key="skill.skill_id">
                <td>{{ skill.skill_id }}</td>
                <td>{{ skill.trained_skill_level }}</td>
                <td>{{ skill.skillpoints_in_skill.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.overview-page { min-height: 100vh; background: #0d1117; color: #c9d1d9; }
.topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 24px; background: #161b22; border-bottom: 1px solid #30363d;
}
.back-btn {
  background: none; border: 1px solid #30363d; color: #8b949e;
  padding: 4px 12px; border-radius: 6px; cursor: pointer;
}
.brand { font-size: 1.1rem; letter-spacing: 3px; color: #58a6ff; }
.content { max-width: 960px; margin: 0 auto; padding: 32px 24px; }
.muted { color: #8b949e; }
.error { color: #f85149; }

.char-header { display: flex; align-items: center; gap: 24px; margin-bottom: 32px; }
.avatar { width: 100px; height: 100px; border-radius: 8px; }
h1 { font-size: 1.8rem; margin: 0 0 8px; }
.char-meta { color: #8b949e; font-size: 0.9rem; margin-top: 4px; }

.stats-grid { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 32px; }
.stat-card {
  flex: 1; min-width: 200px; padding: 20px 24px;
  background: #161b22; border-radius: 8px; border: 1px solid #30363d;
}
.stat-label { font-size: 0.85rem; color: #8b949e; margin-bottom: 8px; }
.stat-value { font-size: 1.4rem; font-weight: 700; color: #58a6ff; }
.stat-updated { font-size: 0.8rem; color: #6e7681; margin-top: 6px; }

.section h3 { color: #c9d1d9; margin-bottom: 12px; }
.skills-table { width: 100%; border-collapse: collapse; }
.skills-table th, .skills-table td {
  text-align: left; padding: 8px 12px;
  border-bottom: 1px solid #21262d; font-size: 0.9rem;
}
.skills-table th { color: #8b949e; font-weight: 500; }
</style>
