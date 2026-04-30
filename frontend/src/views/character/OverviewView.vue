<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCharacterStore } from '@/stores/character'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()
const charStore = useCharacterStore()
const characterId = Number(route.params.id)

onMounted(() => charStore.fetchAll(characterId))

function fmt(n: number | null, suffix = '') {
  if (n === null) return '—'
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) + suffix
}
function fmtSp(sp: number) {
  if (sp >= 1_000_000) return (sp / 1_000_000).toFixed(2) + ' M SP'
  if (sp >= 1_000) return (sp / 1_000).toFixed(1) + ' K SP'
  return sp + ' SP'
}
function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function goTab(tab: string) {
  router.push(`/character/${characterId}/${tab}`)
}

function renderMarkdown(content: string): string {
  const html = marked(content) as string
  return DOMPurify.sanitize(html)
}
</script>

<template>
  <div>
    <n-spin v-if="charStore.loading" :size="24" style="display:block;margin:60px auto;" />
    <n-alert v-else-if="charStore.error" type="error" :title="charStore.error" />

    <template v-else-if="charStore.characterInfo">
      <!-- Character header -->
      <div class="char-header">
        <img
          :src="`https://images.evetech.net/characters/${characterId}/portrait?size=128`"
          class="portrait"
          :alt="charStore.characterInfo.character_name"
        />
        <div class="char-meta">
          <h1 class="char-name h-serif">{{ charStore.characterInfo.character_name }}</h1>
          <div class="meta-row">
            <span v-if="charStore.characterInfo.corporation_id" class="tag">
              Corp {{ charStore.characterInfo.corporation_id }}
            </span>
            <span v-if="charStore.characterInfo.alliance_id" class="tag">
              Alliance {{ charStore.characterInfo.alliance_id }}
            </span>
          </div>
          <div class="updated">更新于 {{ fmtDate(charStore.characterInfo.updated_at) }}</div>
        </div>
      </div>

      <!-- Stat cards -->
      <div class="stats-row">
        <div class="stat-card" @click="goTab('wallet')">
          <div class="stat-label">钱包余额</div>
          <div class="stat-value">{{ fmt(charStore.wallet?.balance ?? null, ' ISK') }}</div>
          <div class="stat-hint">点击查看明细 →</div>
        </div>
        <div class="stat-card" @click="goTab('skills')">
          <div class="stat-label">技能点</div>
          <div class="stat-value">{{ fmtSp(charStore.skills?.total_sp ?? 0) }}</div>
          <div class="stat-hint">{{ charStore.skills?.skills.length ?? 0 }} 个技能 →</div>
        </div>
        <div class="stat-card" @click="goTab('mail')">
          <div class="stat-label">邮件</div>
          <div class="stat-value">查看</div>
          <div class="stat-hint">邮件列表 →</div>
        </div>
        <div class="stat-card" @click="goTab('notifications')">
          <div class="stat-label">通知</div>
          <div class="stat-value">查看</div>
          <div class="stat-hint">通知列表 →</div>
        </div>
      </div>

      <!-- Quick nav tabs -->
      <div class="quick-nav">
        <button class="qnav-btn" @click="goTab('wallet')">钱包</button>
        <button class="qnav-btn" @click="goTab('skills')">技能</button>
        <button class="qnav-btn" @click="goTab('assets')">资产</button>
        <button class="qnav-btn" @click="goTab('mail')">邮件</button>
        <button class="qnav-btn" @click="goTab('notifications')">通知</button>
      </div>

      <!-- Plugin extensions section -->
      <template v-if="charStore.characterInfo?.extensions?.length">
        <div class="extensions-section">
          <div class="extensions-title">插件数据</div>
          <div class="extensions-grid">
            <div
              v-for="ext in charStore.characterInfo.extensions"
              :key="ext.plugin_name + ext.title"
              class="ext-card"
              :class="ext.css_class"
            >
              <div class="ext-header">
                <span class="ext-title">{{ ext.title }}</span>
                <span class="ext-source">{{ ext.plugin_name }}</span>
              </div>
              <div class="ext-content">
                <div v-if="ext.widget === 'markdown'" class="ext-markdown" v-html="renderMarkdown(ext.content)" />
                <div v-else-if="ext.widget === 'stats'" class="ext-stats">
                  <div v-for="stat in ext.content" :key="stat.label" class="ext-stat">
                    <div class="ext-stat-label">{{ stat.label }}</div>
                    <div class="ext-stat-value">{{ stat.value }}</div>
                  </div>
                </div>
                <div
                  v-else-if="ext.widget === 'iframe'"
                  class="ext-iframe"
                  :style="{ height: (ext.content.height || 300) + 'px' }"
                >
                  <iframe :src="ext.content.url" sandbox="allow-scripts allow-same-origin" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.char-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 28px;
}
.portrait {
  width: 96px;
  height: 96px;
  border-radius: 8px;
  border: 1px solid #30302e;
  flex-shrink: 0;
}
.char-meta { flex: 1; }
.char-name {
  font-size: 1.6rem;
  color: #faf9f5;
  margin-bottom: 8px;
  line-height: 1.2;
}
.meta-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }
.tag {
  font-size: 0.78rem;
  color: #87867f;
  background: #30302e;
  padding: 2px 8px;
  border-radius: 4px;
}
.updated { font-size: 0.8rem; color: #5e5d59; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 18px 20px;
  cursor: pointer;
  transition: border-color 0.18s;
}
.stat-card:hover { border-color: #c96442; }
.stat-label { font-size: 0.8rem; color: #87867f; margin-bottom: 8px; }
.stat-value { font-size: 1.2rem; font-weight: 500; color: #faf9f5; margin-bottom: 4px; }
.stat-hint { font-size: 0.75rem; color: #5e5d59; }

.quick-nav {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.qnav-btn {
  background: #1e1e1c;
  border: 1px solid #30302e;
  color: #b0aea5;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.88rem;
  transition: border-color 0.18s, color 0.18s;
}
.qnav-btn:hover {
  border-color: #c96442;
  color: #faf9f5;
}

.extensions-section {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid #30302e;
}
.extensions-title {
  font-size: 0.8rem;
  color: #87867f;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
}
.extensions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.ext-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 18px 20px;
}
.ext-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.ext-title {
  font-size: 1rem;
  font-weight: 500;
  color: #faf9f5;
}
.ext-source {
  font-size: 0.75rem;
  color: #87867f;
}
.ext-markdown {
  color: #b0aea5;
  line-height: 1.6;
  font-size: 0.9rem;
}
.ext-stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
}
.ext-stat { text-align: center; }
.ext-stat-label { font-size: 0.75rem; color: #87867f; margin-bottom: 4px; }
.ext-stat-value { font-size: 1.1rem; font-weight: 500; color: #faf9f5; }
.ext-iframe iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 6px;
}
</style>
