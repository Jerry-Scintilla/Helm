<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCorporationStore } from '@/stores/corporation'
import { useI18n } from 'vue-i18n'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const corpStore = useCorporationStore()
const { t } = useI18n()
const corporationId = Number(route.params.id)

onMounted(() => corpStore.fetchInfo(corporationId))

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString()
}
</script>

<template>
  <div>
    <div v-if="corpStore.loading" class="helm-page-loader"><HelmLoader :size="48" /></div>
    <n-alert v-else-if="corpStore.error" type="error" :title="corpStore.error" />

    <template v-else-if="corpStore.corporationInfo">
      <div class="corp-header">
        <img
          :src="`https://images.evetech.net/corporations/${corporationId}/logo?size=128`"
          class="corp-logo"
          alt=""
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
          <div class="info-value">{{ corpStore.corporationInfo.ceo_id ?? '—' }}</div>
        </div>
        <div class="info-card">
          <div class="info-label">{{ t('corp.allianceId') }}</div>
          <div class="info-value">{{ corpStore.corporationInfo.alliance_id ?? '—' }}</div>
        </div>
      </div>

      <div v-if="corpStore.corporationInfo.description" class="desc-section">
        <div class="section-label">{{ t('corp.description') }}</div>
        <p class="desc-text">{{ corpStore.corporationInfo.description }}</p>
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

.desc-section { margin-top: 8px; }
.section-label { font-size: 0.82rem; color: #87867f; margin-bottom: 8px; }
.desc-text { font-size: 0.9rem; color: #b0aea5; line-height: 1.7; }
</style>
