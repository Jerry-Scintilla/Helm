<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '@/stores/character'

const route = useRoute()
const charStore = useCharacterStore()
const characterId = Number(route.params.id)

onMounted(async () => {
  await Promise.all([
    charStore.fetchAll(characterId),
    charStore.fetchSkillQueue(characterId),
  ])
})

function fmtSp(sp: number) {
  if (sp >= 1_000_000) return (sp / 1_000_000).toFixed(2) + ' M'
  if (sp >= 1_000) return (sp / 1_000).toFixed(1) + ' K'
  return String(sp)
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('zh-CN')
}

function levelDots(level: number) {
  return '●'.repeat(level) + '○'.repeat(5 - level)
}

function queueProgress(entry: { level_start_sp: number | null; level_end_sp: number | null; start_date: string | null; finish_date: string | null }) {
  if (!entry.start_date || !entry.finish_date) return 0
  const total = new Date(entry.finish_date).getTime() - new Date(entry.start_date).getTime()
  const elapsed = Date.now() - new Date(entry.start_date).getTime()
  return Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)))
}
</script>

<template>
  <div>
    <h1 class="page-title h-serif">技能</h1>

    <div v-if="charStore.skills" class="sp-banner">
      <div class="sp-total">{{ fmtSp(charStore.skills.total_sp) }} SP</div>
      <div class="sp-sub">{{ charStore.skills.skills.length }} 个已学技能</div>
    </div>

    <!-- Skill queue -->
    <section class="section">
      <h2 class="section-title">技能队列</h2>
      <div v-if="charStore.skillQueue.length === 0" class="muted">队列为空</div>
      <div v-else class="queue-list">
        <div
          v-for="entry in charStore.skillQueue"
          :key="entry.queue_position"
          class="queue-item"
        >
          <div class="queue-main">
            <span class="queue-pos">{{ entry.queue_position + 1 }}</span>
            <span class="queue-skill">Skill {{ entry.skill_id }}</span>
            <span class="queue-level">Lv {{ entry.finished_level }}</span>
            <span class="queue-finish">{{ fmtDate(entry.finish_date) }}</span>
          </div>
          <n-progress
            v-if="entry.start_date"
            type="line"
            :percentage="queueProgress(entry)"
            :height="3"
            :show-indicator="false"
            color="#c96442"
            rail-color="#30302e"
            style="margin-top:6px;"
          />
        </div>
      </div>
    </section>

    <!-- Skill list -->
    <section class="section">
      <h2 class="section-title">已学技能</h2>
      <div v-if="!charStore.skills || charStore.skills.skills.length === 0" class="muted">无数据</div>
      <div v-else class="skill-list">
        <div
          v-for="skill in charStore.skills.skills"
          :key="skill.skill_id"
          class="skill-row"
        >
          <span class="skill-id">{{ skill.skill_id }}</span>
          <span class="skill-dots">{{ levelDots(skill.trained_skill_level) }}</span>
          <span class="skill-sp">{{ fmtSp(skill.skillpoints_in_skill) }} SP</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; margin-bottom: 20px; }
.sp-banner {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 28px;
}
.sp-total { font-size: 2rem; font-weight: 500; color: #c96442; font-family: Georgia, serif; }
.sp-sub { font-size: 0.85rem; color: #87867f; margin-top: 4px; }

.section { margin-bottom: 32px; }
.section-title {
  font-size: 1rem;
  font-weight: 500;
  color: #b0aea5;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #30302e;
}
.muted { color: #5e5d59; font-size: 0.9rem; }

.queue-list { display: flex; flex-direction: column; gap: 8px; }
.queue-item {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 6px;
  padding: 10px 14px;
}
.queue-main { display: flex; align-items: center; gap: 12px; }
.queue-pos { width: 24px; text-align: center; font-size: 0.75rem; color: #5e5d59; }
.queue-skill { flex: 1; font-size: 0.9rem; color: #faf9f5; }
.queue-level { font-size: 0.85rem; color: #c96442; }
.queue-finish { font-size: 0.78rem; color: #87867f; }

.skill-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 6px;
}
.skill-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #1e1e1c;
  border-radius: 6px;
  border: 1px solid #30302e;
}
.skill-id { font-size: 0.82rem; color: #87867f; min-width: 48px; }
.skill-dots { font-size: 0.7rem; color: #c96442; letter-spacing: 1px; flex: 1; }
.skill-sp { font-size: 0.8rem; color: #87867f; white-space: nowrap; }
</style>
