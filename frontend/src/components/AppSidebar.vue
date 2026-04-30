<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { MenuOption } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { usePluginStore } from '@/stores/plugin'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const pluginStore = usePluginStore()
const collapsed = ref(false)

function icon(emoji: string) {
  return () => h('span', { style: 'font-size:14px;line-height:1;opacity:0.7' }, emoji)
}

const charId = computed(() =>
  route.params.id ? String(route.params.id) : (auth.characterId ? String(auth.characterId) : null)
)
const corpId = computed(() =>
  route.path.startsWith('/corporation/') ? String(route.params.id) : null
)
const allianceId = computed(() =>
  route.path.startsWith('/alliance/') ? String(route.params.id) : null
)

const menuOptions = computed<MenuOption[]>(() => {
  const cid = charId.value
  const corId = corpId.value
  const alId = allianceId.value
  const items: MenuOption[] = [
    { label: 'Dashboard', key: '/dashboard', icon: icon('⬡') },
  ]

  if (cid) {
    const submoduleItems = pluginStore.plugins
      .filter(p => p.is_enabled && p.meta?.character_submodules?.length)
      .flatMap(p =>
        p.meta.character_submodules
          .slice()
          .sort((a, b) => a.order - b.order)
          .map(s => ({
            label: s.label,
            key: `/character/${cid}/${s.slug}`,
            icon: s.icon ? icon(s.icon) : icon('·'),
          }))
      )

    items.push({
      label: '角色',
      key: 'char-group',
      icon: icon('◈'),
      children: [
        { label: '总览', key: `/character/${cid}/overview`, icon: icon('·') },
        { label: '钱包', key: `/character/${cid}/wallet`, icon: icon('·') },
        { label: '技能', key: `/character/${cid}/skills`, icon: icon('·') },
        { label: '资产', key: `/character/${cid}/assets`, icon: icon('·') },
        { label: '邮件', key: `/character/${cid}/mail`, icon: icon('·') },
        { label: '通知', key: `/character/${cid}/notifications`, icon: icon('·') },
        ...submoduleItems,
      ],
    })
  }

  if (corId) {
    items.push({
      label: '公司',
      key: 'corp-group',
      icon: icon('◉'),
      children: [
        { label: '总览', key: `/corporation/${corId}/overview`, icon: icon('·') },
        { label: '成员', key: `/corporation/${corId}/members`, icon: icon('·') },
        { label: '钱包', key: `/corporation/${corId}/wallet`, icon: icon('·') },
        { label: '资产', key: `/corporation/${corId}/assets`, icon: icon('·') },
      ],
    })
  }

  if (alId) {
    items.push({
      label: '联盟',
      key: 'alliance-group',
      icon: icon('◎'),
      children: [
        { label: '总览', key: `/alliance/${alId}/overview`, icon: icon('·') },
      ],
    })
  }

  if (auth.isSuperuser) {
    items.push({
      label: '管理',
      key: 'admin-group',
      icon: icon('⚙'),
      children: [
        { label: '系统', key: '/admin/system', icon: icon('·') },
        { label: '用户', key: '/admin/users', icon: icon('·') },
        { label: '角色权限', key: '/admin/roles', icon: icon('·') },
        { label: 'SDE', key: '/admin/sde', icon: icon('·') },
        { label: 'Buckets', key: '/admin/buckets', icon: icon('·') },
        { label: 'API Token', key: '/admin/tokens', icon: icon('·') },
        { label: '插件', key: '/admin/plugins', icon: icon('·') },
      ],
    })
  }

  // Plugin sidebar items (from enabled plugins that declare sidebar_items in meta)
  const pluginItems = pluginStore.plugins
    .filter(p => p.is_enabled && p.meta?.sidebar_items?.length)
    .flatMap(p =>
      p.meta.sidebar_items
        .slice()
        .sort((a, b) => a.order - b.order)
        .map(s => ({ label: s.label, key: s.route, icon: s.icon ? icon(s.icon) : icon('◦') }))
    )
  if (pluginItems.length > 0) {
    items.push({
      label: '插件',
      key: 'plugin-group',
      icon: icon('⬡'),
      children: pluginItems,
    })
  }

  return items
})

const activeKey = computed(() => route.path)

function handleSelect(key: string) {
  if (!key.startsWith('/')) return
  router.push(key)
}
</script>

<template>
  <div class="sider" :class="{ collapsed }">
    <div class="brand" @click="collapsed = !collapsed">
      <span class="brand-mark">H</span>
      <span v-if="!collapsed" class="brand-text">ELM</span>
      <span v-if="!collapsed" class="collapse-hint">‹</span>
      <span v-else class="collapse-hint rotated">‹</span>
    </div>
    <n-menu
      :options="menuOptions"
      :value="activeKey"
      :indent="16"
      :collapsed="collapsed"
      :collapsed-width="56"
      :width="210"
      accordion
      @update:value="handleSelect"
    />
  </div>
</template>

<style scoped>
.sider {
  width: 210px;
  min-width: 210px;
  height: 100vh;
  background: #141413;
  border-right: 1px solid #30302e;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s, min-width 0.2s;
  overflow: hidden;
}
.sider.collapsed {
  width: 56px;
  min-width: 56px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 16px 18px 12px;
  border-bottom: 1px solid #30302e;
  margin-bottom: 6px;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  overflow: hidden;
}
.brand-mark {
  font-family: Georgia, serif;
  font-size: 1.2rem;
  font-weight: 500;
  color: #c96442;
  flex-shrink: 0;
}
.brand-text {
  font-family: Georgia, serif;
  font-size: 1.2rem;
  font-weight: 500;
  color: #faf9f5;
  letter-spacing: 3px;
  flex: 1;
}
.collapse-hint {
  font-size: 0.75rem;
  color: #5e5d59;
  margin-left: auto;
  transition: transform 0.2s;
}
.collapse-hint.rotated {
  transform: rotate(180deg);
}
</style>
