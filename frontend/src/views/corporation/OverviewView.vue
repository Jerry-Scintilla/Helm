<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCorporationStore } from '@/stores/corporation'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import HelmLoader from '@/components/HelmLoader.vue'
import CachedImg from '@/components/CachedImg.vue'

const route = useRoute()
const corpStore = useCorporationStore()
const { t } = useI18n()
const corporationId = computed(() => Number(route.params.id))

onMounted(() => corpStore.fetchInfo(corporationId.value))
watch(corporationId, (id) => {
  if (id) corpStore.fetchInfo(id)
})

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString()
}

function decodeEveDescription(raw: string | null | undefined): string {
  if (!raw) return ''
  let s = raw
  // Strip Python repr wrapper: u'...' or b'...' or '...'
  const m = s.match(/^[ub]?['"]([\s\S]*)['"]$/)
  if (m && m[1] !== undefined) s = m[1]
  // Decode \uXXXX escape sequences
  s = s.replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)))
  // Decode common escaped chars
  s = s.replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\'/g, "'").replace(/\\"/g, '"').replace(/\\\\/g, '\\')
  return s
}

const renderedDescription = computed(() => {
  const raw = corpStore.corporationInfo?.description
  if (!raw) return ''
  return DOMPurify.sanitize(decodeEveDescription(raw))
})
</script>

<template>
  <div>
    <div v-if="corpStore.loading" class="helm-page-loader"><HelmLoader :size="48" /></div>
    <n-alert v-else-if="corpStore.error" type="error" :title="corpStore.error" />

    <template v-else-if="corpStore.corporationInfo">
      <div class="corp-header">
        <CachedImg
          :src="`https://images.evetech.net/corporations/${corporationId}/logo?size=128`"
          :key="corporationId"
          class="corp-logo"
        />
        <div>
          <h1 class="corp-name h-serif">{{ corpStore.corporationInfo.name }}</h1>
          <div class="corp-ticker">[{{ corpStore.corporationInfo.ticker }}]</div>
          <div class="updated">{{ t('corp.updatedAt') }} {{ fmtDate(corpStore.corporationInfo.updated_at) }}</div>
        </div>
      </div>

      <div class="info-grid">
        <div class="info-card">
          <div class="info-label">{{ t('corp.memberCount') }}</div>
          <div class="info-value">{{ corpStore.corporationInfo.member_count }}</div>
        </div>
        <div class="info-card">
          <div class="info-label">CEO</div>
          <div class="info-value">{{ corpStore.corporationInfo.ceo_name ?? corpStore.corporationInfo.ceo_id ?? '—' }}</div>
          <div v-if="corpStore.corporationInfo.ceo_name && corpStore.corporationInfo.ceo_id" class="info-sub">#{{ corpStore.corporationInfo.ceo_id }}</div>
        </div>
        <div class="info-card">
          <div class="info-label">{{ t('corp.alliance') }}</div>
          <div class="info-value">{{ corpStore.corporationInfo.alliance_name ?? corpStore.corporationInfo.alliance_id ?? '—' }}</div>
          <div v-if="corpStore.corporationInfo.alliance_name && corpStore.corporationInfo.alliance_id" class="info-sub">#{{ corpStore.corporationInfo.alliance_id }}</div>
        </div>
      </div>

      <div v-if="renderedDescription" class="desc-section">
        <div class="section-label">{{ t('corp.description') }}</div>
        <div class="desc-text" v-html="renderedDescription" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.corp-header { display: flex; align-items: flex-start; gap: 20px; margin-bottom: 28px; }
.corp-logo { width: 80px; height: 80px; border-radius: 6px; border: 1px solid #30302e; }
.corp-name { font-size: 1.6rem; color: #faf9f5; margin-bottom: 4px; }
.corp-ticker { font-size: 0.9rem; color: #c96442; margin-bottom: 4px; }
.updated { font-size: 0.8rem; color: #5e5d59; }

.info-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }
.info-card { background: #1e1e1c; border: 1px solid #30302e; border-radius: 8px; padding: 16px 18px; }
.info-label { font-size: 0.78rem; color: #87867f; margin-bottom: 6px; }
.info-value { font-size: 1.1rem; font-weight: 500; color: #faf9f5; }
.info-sub { font-size: 0.72rem; color: #5e5d59; margin-top: 4px; font-variant-numeric: tabular-nums; }

.desc-section { margin-top: 8px; }
.section-label { font-size: 0.82rem; color: #87867f; margin-bottom: 8px; }
.desc-text { font-size: 0.9rem; color: #b0aea5; line-height: 1.7; }
.desc-text :deep(font) { font-size: inherit !important; }
.desc-text :deep(a) { color: #c96442; text-decoration: none; }
.desc-text :deep(a:hover) { text-decoration: underline; }
</style>
