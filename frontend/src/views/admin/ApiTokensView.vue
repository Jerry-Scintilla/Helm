<script setup lang="ts">
import { onMounted, ref, computed, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '@/stores/admin'
import type { AdminApiToken } from '@/stores/admin'
import type { DataTableColumns } from 'naive-ui'
import { NTag, NButton, NSpace, NText, useMessage } from 'naive-ui'
import HelmLoader from '@/components/HelmLoader.vue'

const adminStore = useAdminStore()
const message = useMessage()
const { t } = useI18n()
const loading = ref(true)
const search = ref('')

onMounted(async () => {
  try {
    await adminStore.fetchAllTokens()
  } finally {
    loading.value = false
  }
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return adminStore.allTokens
  return adminStore.allTokens.filter(tk =>
    tk.name.toLowerCase().includes(q) ||
    (tk.username ?? '').toLowerCase().includes(q) ||
    (tk.primary_role ?? '').toLowerCase().includes(q) ||
    tk.token_prefix.toLowerCase().includes(q)
  )
})

async function revoke(id: number) {
  try {
    await adminStore.adminRevokeToken(id)
    message.success(t('admin.tokens.revoked'))
  } catch {
    message.error(t('admin.tokens.revokeFailed'))
  }
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString()
}

function roleLabel(tk: AdminApiToken): string {
  if (tk.is_superuser) return t('admin.tokens.superRole')
  return tk.primary_role ?? t('admin.tokens.noRole')
}

const cols = computed<DataTableColumns<AdminApiToken>>(() => [
  {
    title: () => t('admin.tokens.owner'),
    key: 'username',
    width: 200,
    render: tk => h('div', { class: 'owner-cell' }, [
      h('span', { class: 'owner-name' }, tk.username ?? `#${tk.user_id}`),
      h(NTag, { size: 'tiny', type: tk.is_superuser ? 'warning' : 'default', bordered: false, style: 'margin-top:2px' },
        { default: () => roleLabel(tk) }),
    ]),
  },
  {
    title: () => t('admin.tokens.tokenName'),
    key: 'name',
    render: tk => h('div', {}, [
      h('span', { class: 'tk-name' }, tk.name),
      h('span', { class: 'tk-prefix' }, ` ${tk.token_prefix}…`),
    ]),
  },
  {
    title: () => t('admin.tokens.scopes'),
    key: 'scopes',
    render: tk => {
      const scopes = tk.scopes.split(' ').filter(Boolean)
      if (!scopes.length) return h(NText, { depth: 3 }, { default: () => '—' })
      return h(NSpace, { size: 4 }, {
        default: () => scopes.map(s => h(NTag, { size: 'tiny', bordered: false }, { default: () => s })),
      })
    },
  },
  {
    title: () => t('common.status'),
    key: 'is_active',
    width: 90,
    render: tk => h(NTag, { type: tk.is_active ? 'success' : 'error', size: 'small' },
      { default: () => tk.is_active ? t('admin.tokens.active') : t('admin.tokens.revokedTag') }),
  },
  {
    title: () => t('admin.tokens.lastUsedCol'),
    key: 'last_used_at',
    width: 120,
    render: tk => fmtDate(tk.last_used_at),
  },
  {
    title: () => t('common.createdAt'),
    key: 'created_at',
    width: 120,
    render: tk => fmtDate(tk.created_at),
  },
  {
    title: () => t('common.actions'),
    key: 'actions',
    width: 90,
    render: tk => tk.is_active
      ? h(NButton, { size: 'tiny', type: 'error', ghost: true, onClick: () => revoke(tk.id) },
          { default: () => t('admin.tokens.revoke') })
      : h(NText, { depth: 3 }, { default: () => '—' }),
  },
])
</script>

<template>
  <div>
    <div v-if="loading" class="helm-section-loader"><HelmLoader :size="48" /></div>
    <template v-else>
      <div class="section-header">
        <span class="count-bar">{{ t('admin.tokens.countAll', { n: adminStore.allTokens.length }) }}</span>
        <n-input
          v-model:value="search"
          size="small"
          clearable
          style="width:240px"
          :placeholder="t('admin.tokens.searchPlaceholder')"
        />
      </div>
      <n-data-table
        :columns="cols"
        :data="filtered"
        :bordered="false"
        size="small"
        :row-key="(tk: AdminApiToken) => tk.id"
      />
    </template>
  </div>
</template>

<style scoped>
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.count-bar { font-size: 0.85rem; color: #87867f; }
.owner-cell { display: flex; flex-direction: column; align-items: flex-start; }
.owner-name { font-size: 0.85rem; color: #faf9f5; }
.tk-name { font-size: 0.85rem; color: #faf9f5; }
.tk-prefix { font-size: 0.78rem; color: #87867f; font-family: monospace; }
</style>
