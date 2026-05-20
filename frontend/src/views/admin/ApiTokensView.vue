<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiTokenStore } from '@/stores/apiToken'
import { useMessage } from 'naive-ui'
import HelmLoader from '@/components/HelmLoader.vue'

const tokenStore = useApiTokenStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)
const showCreate = ref(false)
const newName = ref('')
const newScopes = ref<string[]>([])
const creating = ref(false)

const scopeOptions = [
  { label: 'characters:read', value: 'characters:read' },
  { label: 'corporations:read', value: 'corporations:read' },
  { label: 'alliances:read', value: 'alliances:read' },
  { label: 'admin:read', value: 'admin:read' },
]

onMounted(async () => {
  try {
    await tokenStore.fetchTokens()
  } finally {
    loading.value = false
  }
})

async function createToken() {
  if (!newName.value.trim()) return
  creating.value = true
  try {
    await tokenStore.createToken(newName.value.trim(), newScopes.value)
    message.success(t('admin.tokens.created'))
    showCreate.value = false
    newName.value = ''
    newScopes.value = []
  } catch {
    message.error(t('common.createFailed'))
  } finally {
    creating.value = false
  }
}

async function revoke(id: number) {
  try {
    await tokenStore.revokeToken(id)
    message.success(t('admin.tokens.revoked'))
  } catch {
    message.error(t('admin.tokens.revokeFailed'))
  }
}

function copyToken() {
  if (!tokenStore.newTokenValue) return
  navigator.clipboard.writeText(tokenStore.newTokenValue)
  message.success(t('common.copiedToClipboard'))
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString()
}
</script>

<template>
  <div>
    <!-- New token banner (one-time display) -->
    <n-alert
      v-if="tokenStore.newTokenValue"
      type="warning"
      :title="t('admin.tokens.saveWarning')"
      closable
      @close="tokenStore.clearNewToken()"
      style="margin-bottom:16px"
    >
      <div class="token-value">{{ tokenStore.newTokenValue }}</div>
      <n-button size="small" style="margin-top:8px" @click="copyToken">{{ t('common.copy') }}</n-button>
    </n-alert>

    <div class="section-header">
      <span class="count-bar">{{ t('admin.tokens.count', { n: tokenStore.tokens.length }) }}</span>
      <n-button size="small" type="primary" @click="showCreate = !showCreate">{{ t('common.createNew') }}</n-button>
    </div>

    <n-collapse-transition :show="showCreate">
      <div class="create-form">
        <n-input v-model:value="newName" :placeholder="t('admin.tokens.namePlaceholder')" size="small" style="width:200px" />
        <n-select
          v-model:value="newScopes"
          :options="scopeOptions"
          multiple
          size="small"
          style="width:280px"
          :placeholder="t('admin.tokens.selectScope')"
        />
        <n-button size="small" type="primary" :loading="creating" @click="createToken">{{ t('common.create') }}</n-button>
        <n-button size="small" @click="showCreate = false">{{ t('common.cancel') }}</n-button>
      </div>
    </n-collapse-transition>

    <div v-if="loading" class="helm-section-loader"><HelmLoader :size="48" /></div>
    <div v-else class="token-list">
      <div v-for="token in tokenStore.tokens" :key="token.id" class="token-card">
        <div class="token-header">
          <div>
            <span class="token-name">{{ token.name }}</span>
            <span class="token-prefix">{{ token.token_prefix }}…</span>
          </div>
          <n-tag :type="token.is_active ? 'success' : 'error'" size="tiny">
            {{ token.is_active ? t('admin.tokens.active') : t('admin.tokens.revokedTag') }}
          </n-tag>
        </div>
        <div class="token-scopes">
          <span v-for="s in token.scopes.split(' ').filter(Boolean)" :key="s" class="scope-tag">{{ s }}</span>
        </div>
        <div class="token-footer">
          <span class="token-meta">{{ t('admin.tokens.createdPrefix') }} {{ fmtDate(token.created_at) }}</span>
          <span v-if="token.last_used_at" class="token-meta">{{ t('admin.tokens.lastUsed') }} {{ fmtDate(token.last_used_at) }}</span>
          <n-button
            v-if="token.is_active"
            size="tiny"
            type="error"
            ghost
            @click="revoke(token.id)"
          >
            {{ t('admin.tokens.revoke') }}
          </n-button>
        </div>
      </div>
      <div v-if="tokenStore.tokens.length === 0" class="muted">{{ t('admin.tokens.empty') }}</div>
    </div>
  </div>
</template>

<style scoped>
.token-value {
  font-family: monospace;
  font-size: 0.82rem;
  color: #faf9f5;
  word-break: break-all;
  background: #141413;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 8px;
}
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.count-bar { font-size: 0.85rem; color: #87867f; }
.create-form { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; padding: 12px 16px; background: #1e1e1c; border-radius: 6px; }

.token-list { display: flex; flex-direction: column; gap: 8px; }
.token-card {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 14px 16px;
}
.token-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.token-name { font-size: 0.9rem; font-weight: 500; color: #faf9f5; margin-right: 8px; }
.token-prefix { font-size: 0.8rem; color: #87867f; font-family: monospace; }
.token-scopes { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }
.scope-tag { font-size: 0.72rem; color: #b0aea5; background: #30302e; padding: 2px 6px; border-radius: 3px; }
.token-footer { display: flex; align-items: center; gap: 12px; }
.token-meta { font-size: 0.75rem; color: #5e5d59; }
.muted { color: #5e5d59; font-size: 0.9rem; }
</style>
