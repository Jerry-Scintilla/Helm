<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore, type MailLinkResult } from '@/stores/character'
import { useI18n } from 'vue-i18n'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const charStore = useCharacterStore()
const { t, locale } = useI18n()
const characterId = Number(route.params.id)
const loading = ref(true)
const loadingBody = ref(false)

// Resolved mail-link popup state
const linkPanel = ref<{ loading: boolean; data: MailLinkResult | null; error: string | null } | null>(null)

const LINK_SCHEME_RE = /^(showinfo|contract|hypernet|fitting|bookmark|fleet):/i

function onBodyClick(e: MouseEvent) {
  const anchor = (e.target as HTMLElement).closest('a')
  if (!anchor) return
  const href = anchor.getAttribute('href') || ''
  if (!LINK_SCHEME_RE.test(href)) return
  e.preventDefault()
  void openLinkPanel(href)
}

async function openLinkPanel(linkRef: string) {
  linkPanel.value = { loading: true, data: null, error: null }
  try {
    const data = await charStore.resolveMailLink(characterId, linkRef, locale.value)
    linkPanel.value = { loading: false, data, error: null }
  } catch {
    linkPanel.value = { loading: false, data: null, error: t('mail.linkError') }
  }
}

function closeLinkPanel() {
  linkPanel.value = null
}

onMounted(async () => {
  try {
    await charStore.fetchMails(characterId)
  } finally {
    loading.value = false
  }
})

async function openMail(mailId: number) {
  loadingBody.value = true
  try {
    await charStore.fetchMailBody(characterId, mailId)
  } finally {
    loadingBody.value = false
  }
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString()
}
</script>

<template>
  <div>
    <h1 class="page-title h-serif">{{ t('nav.mail') }}</h1>

    <div v-if="loading" class="helm-page-loader"><HelmLoader :size="48" /></div>
    <div v-else class="mail-layout">
      <!-- Mail list -->
      <div class="mail-list">
        <div
          v-for="mail in charStore.mails"
          :key="mail.mail_id"
          class="mail-item"
          :class="{ unread: !mail.is_read, active: charStore.selectedMail?.mail_id === mail.mail_id }"
          @click="openMail(mail.mail_id)"
        >
          <div class="mail-subject">{{ mail.subject || t('mail.noSubject') }}</div>
          <div class="mail-meta">
            <span>From {{ mail.from_name ?? mail.from_id ?? '?' }}</span>
            <span>{{ fmtDate(mail.timestamp) }}</span>
          </div>
        </div>
        <div v-if="charStore.mails.length === 0" class="muted">{{ t('mail.empty') }}</div>
      </div>

      <!-- Mail detail -->
      <div class="mail-detail">
        <div v-if="loadingBody" class="helm-section-loader"><HelmLoader :size="36" /></div>
        <div v-else-if="charStore.selectedMail" class="mail-body-wrap">
          <h2 class="detail-subject">{{ charStore.selectedMail.subject || t('mail.noSubject') }}</h2>
          <div class="detail-meta">
            <span>{{ t('mail.from') }} {{ charStore.selectedMail.from_name ?? charStore.selectedMail.from_id ?? '?' }}</span>
            <span>{{ fmtDate(charStore.selectedMail.timestamp) }}</span>
          </div>
          <div class="detail-body" v-html="charStore.selectedMail.body" @click="onBodyClick" />
        </div>
        <div v-else class="no-selection">{{ t('mail.clickToRead') }}</div>
      </div>
    </div>

    <!-- Resolved link popup -->
    <div v-if="linkPanel" class="link-overlay" @click.self="closeLinkPanel">
      <div class="link-panel">
        <button class="link-close" @click="closeLinkPanel" aria-label="close">×</button>

        <div v-if="linkPanel.loading" class="link-loading"><HelmLoader :size="32" /></div>

        <div v-else-if="linkPanel.error" class="link-error">{{ linkPanel.error }}</div>

        <template v-else-if="linkPanel.data">
          <div class="link-header">
            <img v-if="linkPanel.data.icon_url" :src="linkPanel.data.icon_url" class="link-icon" alt="" />
            <div class="link-titles">
              <div class="link-title">{{ linkPanel.data.title }}</div>
              <div v-if="linkPanel.data.subtitle" class="link-subtitle">{{ linkPanel.data.subtitle }}</div>
            </div>
          </div>

          <div v-if="linkPanel.data.description" class="link-desc">{{ linkPanel.data.description }}</div>

          <div class="link-fields">
            <div v-for="(f, i) in linkPanel.data.fields" :key="i" class="link-field">
              <span class="link-field-label">{{ f.label }}</span>
              <span class="link-field-value">{{ f.value }}</span>
            </div>
          </div>

          <div v-if="linkPanel.data.items.length" class="link-items">
            <div class="link-items-title">{{ t('mail.contractItems') }}</div>
            <div v-for="(it, i) in linkPanel.data.items" :key="i" class="link-item" :class="{ excluded: !it.is_included }">
              <img v-if="it.icon_url" :src="it.icon_url" class="link-item-icon" alt="" />
              <span class="link-item-name">{{ it.type_name }}</span>
              <span v-if="it.quantity" class="link-item-qty">× {{ it.quantity.toLocaleString() }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; margin-bottom: 20px; }

.mail-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  height: calc(100vh - 180px);
}

.mail-list {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  overflow-y: auto;
}
.mail-item {
  padding: 12px 16px;
  border-bottom: 1px solid #30302e;
  cursor: pointer;
  transition: background 0.15s;
}
.mail-item:hover { background: #252523; }
.mail-item.active { background: rgba(201,100,66,0.1); border-left: 2px solid #c96442; }
.mail-item.unread .mail-subject { color: #faf9f5; font-weight: 500; }
.mail-subject { font-size: 0.88rem; color: #b0aea5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mail-meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: #5e5d59; margin-top: 4px; }
.muted { padding: 24px 16px; color: #5e5d59; font-size: 0.9rem; }

.mail-detail {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 20px 24px;
  overflow-y: auto;
}
.no-selection { color: #5e5d59; font-size: 0.9rem; }
.detail-subject { font-size: 1.1rem; font-weight: 500; color: #faf9f5; margin-bottom: 8px; }
.detail-meta { display: flex; gap: 16px; font-size: 0.8rem; color: #87867f; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #30302e; }
.detail-body { font-size: 0.9rem; color: #b0aea5; line-height: 1.7; }
.detail-body :deep(a) { color: #c96442; text-decoration: none; cursor: pointer; }
.detail-body :deep(a:hover) { text-decoration: underline; }
.detail-body :deep(font[size]) { font-size: inherit; }

/* Resolved-link popup */
.link-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.link-panel {
  position: relative;
  width: min(460px, 92vw);
  max-height: 80vh;
  overflow-y: auto;
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 10px;
  padding: 20px 22px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}
.link-close {
  position: absolute;
  top: 10px;
  right: 12px;
  background: none;
  border: none;
  color: #87867f;
  font-size: 1.3rem;
  line-height: 1;
  cursor: pointer;
}
.link-close:hover { color: #faf9f5; }
.link-loading { display: flex; justify-content: center; padding: 24px 0; }
.link-error { color: #c96442; font-size: 0.9rem; padding: 12px 0; }

.link-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-right: 20px; }
.link-icon { width: 48px; height: 48px; border-radius: 6px; flex-shrink: 0; }
.link-title { font-size: 1.05rem; font-weight: 500; color: #faf9f5; }
.link-subtitle { font-size: 0.8rem; color: #87867f; margin-top: 2px; }

.link-desc {
  font-size: 0.82rem;
  color: #9b9990;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #2a2a28;
}
.link-fields { display: flex; flex-direction: column; gap: 8px; }
.link-field { display: flex; justify-content: space-between; gap: 16px; font-size: 0.85rem; border-bottom: 1px solid #2a2a28; padding-bottom: 8px; }
.link-field-label { color: #87867f; flex-shrink: 0; }
.link-field-value { color: #b0aea5; text-align: right; word-break: break-word; }

.link-items { margin-top: 16px; }
.link-items-title { font-size: 0.8rem; color: #87867f; margin-bottom: 8px; }
.link-item { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #b0aea5; padding: 4px 0; }
.link-item.excluded { opacity: 0.5; }
.link-item-icon { width: 24px; height: 24px; border-radius: 4px; }
.link-item-name { flex: 1; }
.link-item-qty { color: #87867f; }
</style>
