<script setup lang="ts">
import { computed, h, ref } from 'vue'
import HelmWheel from './HelmWheel.vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { MenuOption } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { usePluginStore } from '@/stores/plugin'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const pluginStore = usePluginStore()
const { t } = useI18n()
const collapsed = ref(false)

function icon(emoji: string) {
  return () => h('span', { style: 'font-size:14px;line-height:1;opacity:0.7' }, emoji)
}

const charId = computed(() =>
  route.params.id ? String(route.params.id) : (auth.characterId ? String(auth.characterId) : null)
)
const corpId = computed(() => {
  if (route.path.startsWith('/corporation/')) return String(route.params.id)
  return auth.primaryCorporationId ? String(auth.primaryCorporationId) : null
})
const allianceId = computed(() => {
  if (route.path.startsWith('/alliance/')) return String(route.params.id)
  return auth.primaryAllianceId ? String(auth.primaryAllianceId) : null
})

const menuOptions = computed<MenuOption[]>(() => {
  const cid = charId.value
  const corId = corpId.value
  const alId = allianceId.value
  const items: MenuOption[] = [
    { label: t('nav.dashboard'), key: '/dashboard', icon: icon('⬡') },
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
      label: t('nav.character'),
      key: 'char-group',
      icon: icon('◈'),
      children: [
        { label: t('nav.overview'), key: `/character/${cid}/overview`, icon: icon('·') },
        { label: t('nav.wallet'), key: `/character/${cid}/wallet`, icon: icon('·') },
        { label: t('nav.skills'), key: `/character/${cid}/skills`, icon: icon('·') },
        { label: t('nav.assets'), key: `/character/${cid}/assets`, icon: icon('·') },
        { label: t('nav.mail'), key: `/character/${cid}/mail`, icon: icon('·') },
        { label: t('nav.notifications'), key: `/character/${cid}/notifications`, icon: icon('·') },
        ...submoduleItems,
      ],
    })
  }

  if (corId) {
    items.push({
      label: t('nav.corporation'),
      key: 'corp-group',
      icon: icon('◉'),
      children: [
        { label: t('nav.overview'), key: `/corporation/${corId}/overview`, icon: icon('·') },
        { label: t('nav.members'), key: `/corporation/${corId}/members`, icon: icon('·') },
        { label: t('nav.wallet'), key: `/corporation/${corId}/wallet`, icon: icon('·') },
        { label: t('nav.assets'), key: `/corporation/${corId}/assets`, icon: icon('·') },
      ],
    })
  }

  if (alId) {
    items.push({
      label: t('nav.alliance'),
      key: 'alliance-group',
      icon: icon('◎'),
      children: [
        { label: t('nav.overview'), key: `/alliance/${alId}/overview`, icon: icon('·') },
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
  items.push(...pluginItems)

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
      <HelmWheel :size="20" color="#c96442" variant="auto" class="brand-wheel" />
      <span v-if="!collapsed" class="brand-wordmark">Helm<span class="brand-stop">.</span></span>
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
.brand-wheel {
  flex-shrink: 0;
}
.brand-wordmark {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.15rem;
  font-weight: 500;
  color: #faf9f5;
  letter-spacing: -0.01em;
  flex: 1;
  white-space: nowrap;
}
.brand-stop {
  color: #c96442;
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
