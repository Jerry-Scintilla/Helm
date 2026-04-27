<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useApiTokenStore } from '@/stores/apiToken'
import { useMessage } from 'naive-ui'

const tokenStore = useApiTokenStore()
const message = useMessage()
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
    message.success('Token 已创建，请妥善保存完整值')
    showCreate.value = false
    newName.value = ''
    newScopes.value = []
  } catch {
    message.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function revoke(id: number) {
  try {
    await tokenStore.revokeToken(id)
    message.success('Token 已撤销')
  } catch {
    message.error('撤销失败')
  }
}

function copyToken() {
  if (!tokenStore.newTokenValue) return
  navigator.clipboard.writeText(tokenStore.newTokenValue)
  message.success('已复制到剪贴板')
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('zh-CN')
}
</script>

<template>
  <div>
    <!-- New token banner (one-time display) -->
    <n-alert
      v-if="tokenStore.newTokenValue"
      type="warning"
      title="请立即保存以下 Token 完整值，关闭后无法再次查看"
      closable
      @close="tokenStore.clearNewToken()"
      style="margin-bottom:16px"
    >
      <div class="token-value">{{ tokenStore.newTokenValue }}</div>
      <n-button size="small" style="margin-top:8px" @click="copyToken">复制</n-button>
    </n-alert>

    <div class="section-header">
      <span class="count-bar">{{ tokenStore.tokens.length }} 个 API Token</span>
      <n-button size="small" type="primary" @click="showCreate = !showCreate">+ 新建</n-button>
    </div>

    <n-collapse-transition :show="showCreate">
      <div class="create-form">
        <n-input v-model:value="newName" placeholder="Token 名称" size="small" style="width:200px" />
        <n-select
          v-model:value="newScopes"
          :options="scopeOptions"
          multiple
          size="small"
          style="width:280px"
          placeholder="选择作用域"
        />
        <n-button size="small" type="primary" :loading="creating" @click="createToken">创建</n-button>
        <n-button size="small" @click="showCreate = false">取消</n-button>
      </div>
    </n-collapse-transition>

    <n-spin v-if="loading" :size="24" style="display:block;margin:40px auto;" />
    <div v-else class="token-list">
      <div v-for="token in tokenStore.tokens" :key="token.id" class="token-card">
        <div class="token-header">
          <div>
            <span class="token-name">{{ token.name }}</span>
            <span class="token-prefix">{{ token.token_prefix }}…</span>
          </div>
          <n-tag :type="token.is_active ? 'success' : 'error'" size="tiny">
            {{ token.is_active ? '活跃' : '已撤销' }}
          </n-tag>
        </div>
        <div class="token-scopes">
          <span v-for="s in token.scopes.split(' ').filter(Boolean)" :key="s" class="scope-tag">{{ s }}</span>
        </div>
        <div class="token-footer">
          <span class="token-meta">创建 {{ fmtDate(token.created_at) }}</span>
          <span v-if="token.last_used_at" class="token-meta">最后使用 {{ fmtDate(token.last_used_at) }}</span>
          <n-button
            v-if="token.is_active"
            size="tiny"
            type="error"
            ghost
            @click="revoke(token.id)"
          >
            撤销
          </n-button>
        </div>
      </div>
      <div v-if="tokenStore.tokens.length === 0" class="muted">暂无 API Token</div>
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
