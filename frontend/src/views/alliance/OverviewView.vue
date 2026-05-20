<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAllianceStore } from '@/stores/alliance'
import { useI18n } from 'vue-i18n'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const allianceStore = useAllianceStore()
const { t } = useI18n()
const allianceId = Number(route.params.id)

onMounted(() => allianceStore.fetchInfo(allianceId))

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString()
}
</script>

<template>
  <div>
    <div v-if="allianceStore.loading" class="helm-page-loader"><HelmLoader :size="48" /></div>
    <n-alert v-else-if="allianceStore.error" type="error" :title="allianceStore.error" />

    <template v-else-if="allianceStore.allianceInfo">
      <div class="alliance-header">
        <img
          :src="`https://images.evetech.net/alliances/${allianceId}/logo?size=128`"
          class="alliance-logo"
          alt=""
        />
        <div>
          <h1 class="alliance-name h-serif">{{ allianceStore.allianceInfo.name }}</h1>
          <div class="alliance-ticker">[{{ allianceStore.allianceInfo.ticker }}]</div>
          <div class="updated">{{ t('alliance.updatedAt') }} {{ fmtDate(allianceStore.allianceInfo.updated_at) }}</div>
        </div>
      </div>

      <div class="info-grid">
        <div class="info-card">
          <div class="info-label">{{ t('alliance.memberCorps') }}</div>
          <div class="info-value">{{ allianceStore.allianceInfo.member_corporations.length }}</div>
        </div>
        <div class="info-card">
          <div class="info-label">{{ t('alliance.executorCorp') }}</div>
          <div class="info-value">{{ allianceStore.allianceInfo.executor_corp_id ?? '—' }}</div>
        </div>
        <div class="info-card">
          <div class="info-label">{{ t('alliance.creatorCorp') }}</div>
          <div class="info-value">{{ allianceStore.allianceInfo.creator_corp_id ?? '—' }}</div>
        </div>
      </div>

      <section>
        <div class="section-label">{{ t('alliance.memberList', { n: allianceStore.allianceInfo.member_corporations.length }) }}</div>
        <div class="corp-grid">
          <div
            v-for="corpId in allianceStore.allianceInfo.member_corporations"
            :key="corpId"
            class="corp-chip"
          >
            {{ corpId }}
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.alliance-header { display: flex; align-items: flex-start; gap: 20px; margin-bottom: 28px; }
.alliance-logo { width: 80px; height: 80px; border-radius: 6px; border: 1px solid #30302e; }
.alliance-name { font-size: 1.6rem; color: #faf9f5; margin-bottom: 4px; }
.alliance-ticker { font-size: 0.9rem; color: #c96442; margin-bottom: 4px; }
.updated { font-size: 0.8rem; color: #5e5d59; }

.info-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }
.info-card { background: #1e1e1c; border: 1px solid #30302e; border-radius: 8px; padding: 16px 18px; }
.info-label { font-size: 0.78rem; color: #87867f; margin-bottom: 6px; }
.info-value { font-size: 1.1rem; font-weight: 500; color: #faf9f5; }

.section-label { font-size: 0.82rem; color: #87867f; margin-bottom: 10px; }
.corp-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.corp-chip {
  font-size: 0.8rem;
  color: #b0aea5;
  background: #30302e;
  padding: 4px 10px;
  border-radius: 4px;
}
</style>
