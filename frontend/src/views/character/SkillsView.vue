<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '@/stores/character'
import { useI18n } from 'vue-i18n'
import { resolveSdeName } from '@/utils/sde'
import type { SkillGroup } from '@/stores/character'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const charStore = useCharacterStore()
const { t } = useI18n()
const characterId = Number(route.params.id)

const searchQuery = ref('')
const filterMode = ref<'all' | 'maxed' | 'unmaxed'>('all')
const expandedGroup = ref<number | null>(null)

onMounted(async () => {
  await Promise.all([
    charStore.fetchAll(characterId),
    charStore.fetchSkillQueue(characterId),
  ])
})

function fmtSp(sp: number) {
  if (sp >= 1_000_000) return (sp / 1_000_000).toFixed(2) + 'M'
  if (sp >= 1_000) return (sp / 1_000).toFixed(1) + 'K'
  return String(sp)
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString()
}

function queueProgress(entry: { start_date: string | null; finish_date: string | null }) {
  if (!entry.start_date || !entry.finish_date) return 0
  const total = new Date(entry.finish_date).getTime() - new Date(entry.start_date).getTime()
  const elapsed = Date.now() - new Date(entry.start_date).getTime()
  return Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)))
}

function groupLabel(g: SkillGroup): string {
  return resolveSdeName(g.group_name, `Group ${g.group_id}`)
}

function isGroupAllMaxed(g: SkillGroup): boolean {
  return g.skills.every(s => s.trained_skill_level === 5)
}

function groupProgress(g: SkillGroup): number {
  if (!g.skills.length) return 0
  const total = g.skills.reduce((n, s) => n + s.trained_skill_level, 0)
  return Math.round((total / (g.skills.length * 5)) * 100)
}

const filteredGroups = computed<SkillGroup[]>(() => {
  if (!charStore.skills) return []
  const q = searchQuery.value.trim().toLowerCase()

  return charStore.skills.groups
    .map(g => {
      let skills = g.skills
      if (filterMode.value === 'maxed') skills = skills.filter(s => s.trained_skill_level === 5)
      if (filterMode.value === 'unmaxed') skills = skills.filter(s => s.trained_skill_level < 5)
      if (q) {
        skills = skills.filter(s =>
          resolveSdeName(s.skill_name, '').toLowerCase().includes(q)
        )
        const groupMatches = groupLabel(g).toLowerCase().includes(q)
        if (groupMatches && skills.length === 0) skills = g.skills
      }
      return { ...g, skills }
    })
    .filter(g => g.skills.length > 0)
})

function isExpanded(gid: number): boolean {
  if (searchQuery.value || filterMode.value !== 'all') return true
  return expandedGroup.value === gid
}

function toggleGroup(gid: number) {
  if (searchQuery.value || filterMode.value !== 'all') return
  expandedGroup.value = expandedGroup.value === gid ? null : gid
}

const filterOptions = computed(() => [
  { label: t('skills.filter.all'), value: 'all' },
  { label: t('skills.filter.maxed'), value: 'maxed' },
  { label: t('skills.filter.unmaxed'), value: 'unmaxed' },
])

const totalSkillCount = computed(() =>
  charStore.skills?.groups.reduce((n, g) => n + g.skills.length, 0) ?? 0
)

function onEnter(el: Element) {
  const e = el as HTMLElement
  e.style.height = '0'
  e.style.overflow = 'hidden'
  requestAnimationFrame(() => { e.style.height = e.scrollHeight + 'px' })
}
function onAfterEnter(el: Element) {
  const e = el as HTMLElement
  e.style.height = ''
  e.style.overflow = ''
}
function onLeave(el: Element) {
  const e = el as HTMLElement
  e.style.height = e.scrollHeight + 'px'
  e.style.overflow = 'hidden'
  requestAnimationFrame(() => { e.style.height = '0' })
}
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h1 class="page-title h-serif">{{ t('nav.skills') }}</h1>
        <div v-if="charStore.skills" class="sp-sub">
          {{ t('skills.totalSp', { n: charStore.skills.total_sp.toLocaleString() }) }} · {{ t('skills.trainedCount', { n: totalSkillCount }) }}
        </div>
      </div>

      <div class="toolbar">
        <n-select
          v-model:value="filterMode"
          :options="filterOptions"
          size="small"
          style="width:120px"
        />
        <n-input
          v-model:value="searchQuery"
          :placeholder="t('common.search')"
          size="small"
          clearable
          style="width:160px"
        >
          <template #prefix>
            <n-icon><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></n-icon>
          </template>
        </n-input>
      </div>
    </div>

    <!-- Skill queue -->
    <section v-if="charStore.skillQueue.length > 0" class="section">
      <h2 class="section-title">{{ t('skills.queue') }}</h2>
      <div class="queue-list">
        <div v-for="entry in charStore.skillQueue" :key="entry.queue_position" class="queue-item">
          <div class="queue-main">
            <span class="queue-pos">{{ entry.queue_position + 1 }}</span>
            <span class="queue-skill">{{ resolveSdeName(entry.skill_name, `Skill ${entry.skill_id}`) }}</span>
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
            style="margin-top:6px"
          />
        </div>
      </div>
    </section>

    <!-- Skill groups -->
    <section class="section">
      <div v-if="!charStore.skills" class="helm-page-loader"><HelmLoader :size="48" /></div>
      <div v-else-if="filteredGroups.length === 0" class="muted">{{ t('skills.notFound') }}</div>
      <div v-else class="group-grid">
        <div
          v-for="group in filteredGroups"
          :key="group.group_id"
          class="group-card"
          :class="{ expanded: isExpanded(group.group_id) }"
        >
          <div class="group-header" @click="toggleGroup(group.group_id)">
            <span class="group-name">
              {{ groupLabel(group) }}<span v-if="isGroupAllMaxed(group)" class="maxed-mark">*</span>
            </span>
            <span class="group-count">{{ group.skills.length }}</span>
          </div>
          <div class="group-progress-track">
            <div class="group-progress-fill" :style="{ width: groupProgress(group) + '%' }" />
          </div>

          <Transition @enter="onEnter" @after-enter="onAfterEnter" @leave="onLeave">
          <div v-if="isExpanded(group.group_id)" class="skill-list">
            <div
              v-for="skill in group.skills"
              :key="skill.skill_id"
              class="skill-row"
            >
              <span class="skill-name">{{ resolveSdeName(skill.skill_name, `#${skill.skill_id}`) }}</span>
              <span class="skill-right">
                <span class="skill-pips">
                  <span
                    v-for="i in 5"
                    :key="i"
                    class="pip"
                    :class="{ filled: i <= skill.trained_skill_level }"
                  />
                </span>
                <span class="skill-sp">{{ fmtSp(skill.skillpoints_in_skill) }}</span>
              </span>
            </div>
          </div>
          </Transition>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.page-title { font-size: 1.6rem; color: #faf9f5; margin: 0; }
.sp-sub { font-size: 0.85rem; color: #87867f; margin-top: 4px; }

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}

.section { margin-bottom: 28px; }
.section-title {
  font-size: 1rem; font-weight: 500; color: #b0aea5;
  margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #30302e;
}
.muted { color: #5e5d59; font-size: 0.9rem; }

.queue-list { display: flex; flex-direction: column; gap: 8px; }
.queue-item {
  background: #1e1e1c; border: 1px solid #30302e;
  border-radius: 6px; padding: 10px 14px;
}
.queue-main { display: flex; align-items: center; gap: 12px; }
.queue-pos { width: 24px; text-align: center; font-size: 0.75rem; color: #5e5d59; }
.queue-skill { flex: 1; font-size: 0.9rem; color: #faf9f5; }
.queue-level { font-size: 0.85rem; color: #c96442; }
.queue-finish { font-size: 0.78rem; color: #87867f; }

.group-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  align-items: start;
}

.group-card {
  background: #1a1a18;
  border: 1px solid #2e2e2c;
  border-radius: 4px;
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  background: #222220;
  transition: background 0.12s;
}
.group-header:hover { background: #282826; }

.group-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: #c8c5bb;
}
.maxed-mark {
  color: #c96442;
  margin-left: 2px;
  font-size: 0.75rem;
}
.group-count {
  font-size: 0.85rem;
  color: #87867f;
  font-variant-numeric: tabular-nums;
  min-width: 20px;
  text-align: right;
}

.group-progress-track {
  height: 2px;
  background: #2a2a28;
}
.group-progress-fill {
  height: 100%;
  background: #c96442;
  transition: width 0.3s ease;
}

.skill-list {
  border-top: 1px solid #2e2e2c;
  transition: height 0.22s ease;
}
.skill-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  gap: 8px;
}
.skill-row:last-child { border-bottom: none; }

.skill-name {
  font-size: 0.8rem;
  color: #a8a5a0;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.skill-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.skill-pips {
  display: flex;
  gap: 2px;
}
.pip {
  width: 8px;
  height: 8px;
  border-radius: 1px;
  background: #3a3a38;
  border: 1px solid #4a4a48;
}
.pip.filled {
  background: #c96442;
  border-color: #c96442;
}
.skill-sp {
  font-size: 0.75rem;
  color: #5e5d59;
  min-width: 44px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 900px) {
  .group-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 560px) {
  .group-grid { grid-template-columns: 1fr; }
}
</style>
