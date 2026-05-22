<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'
import { usePortraitStore } from '@/stores/portrait'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()
const localeStore = useLocaleStore()
const portraitStore = usePortraitStore()
const { t } = useI18n()

interface Character {
  character_id: number
  character_name: string
}

const characters = ref<Character[]>([])

onMounted(async () => {
  try {
    const res = await api.get('/api/v1/characters/')
    characters.value = res.data
    const primary = res.data.find((c: any) => c.is_primary) ?? res.data[0]
    if (primary) auth.updatePrimaryCorpAlliance(primary.corporation_id ?? null, primary.alliance_id ?? null)
  } catch {}
  if (auth.characterId) portraitStore.fetchPortrait(auth.characterId)
})

watch(() => auth.characterId, (id) => {
  if (id) portraitStore.fetchPortrait(id)
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

const adminMenuOptions = computed(() => [
  { label: t('admin.tabs.system'), key: '/admin/system' },
  { label: t('admin.tabs.users'), key: '/admin/users' },
  { label: t('admin.tabs.roles'), key: '/admin/roles' },
  { label: t('admin.tabs.sde'), key: '/admin/sde' },
  { label: t('admin.tabs.buckets'), key: '/admin/buckets' },
  { label: t('admin.tabs.tokens'), key: '/admin/tokens' },
  { label: t('admin.tabs.plugins'), key: '/admin/plugins' },
  { label: t('admin.tabs.tasks'), key: '/admin/tasks' },
  { label: t('admin.tabs.market'), key: '/admin/market' },
])

function handleAdminMenu(key: string) {
  router.push(key)
}

const userMenuOptions = computed(() => [{ label: t('header.logout'), key: 'logout' }])

const charMenuOptions = computed(() => [
  ...characters.value.map(c => ({ label: c.character_name, key: String(c.character_id) })),
  { type: 'divider', key: 'd1' },
  { label: t('dashboard.addCharacter'), key: '__bind__' },
])

async function handleCharMenu(key: string) {
  if (key === '__bind__') {
    try {
      const url = await auth.bindCharacter()
      window.location.href = url
    } catch {}
  } else {
    router.push(`/character/${key}/overview`)
  }
}

function handleUserMenu(key: string) {
  if (key === 'logout') handleLogout()
}

const langOptions = [
  { label: '中文', key: 'zh' },
  { label: 'English', key: 'en' },
]

function handleLangSelect(key: string) {
  localeStore.setLocale(key as 'zh' | 'en')
}
</script>

<template>
  <div class="header">
    <div class="header-left">
      <slot name="title" />
      <span class="header-divider" aria-hidden="true">|</span>
      <a
        class="header-copyright"
        href="https://github.com/Jerry-Scintilla/Helm"
        target="_blank"
        rel="noopener noreferrer"
      >版权信息 © 2026 | Helm</a>
    </div>
    <div class="header-right">
      <!-- Language dropdown -->
      <n-dropdown trigger="click" :options="langOptions" @select="handleLangSelect">
        <button class="lang-btn">
          {{ localeStore.locale === 'zh' ? '中文' : 'English' }}
          <span class="caret">▾</span>
        </button>
      </n-dropdown>

      <!-- Admin menu (superuser only) -->
      <n-dropdown
        v-if="auth.isSuperuser"
        trigger="hover"
        :options="adminMenuOptions"
        @select="handleAdminMenu"
      >
        <button class="icon-btn" :title="t('header.adminTitle')" @click="router.push('/admin/system')">⚙</button>
      </n-dropdown>

      <!-- Character switcher -->
      <n-dropdown trigger="click" :options="charMenuOptions" @select="handleCharMenu">
        <div class="char-pill">
          <img
            v-if="auth.characterId"
            :src="portraitStore.getUrl(auth.characterId!, 32)"
            class="char-avatar"
            alt=""
          />
          <span class="char-name">{{ auth.characterName }}</span>
          <span class="caret">▾</span>
        </div>
      </n-dropdown>

      <!-- User menu -->
      <n-dropdown trigger="click" :options="userMenuOptions" @select="handleUserMenu">
        <button class="icon-btn" :title="t('header.userMenu')">⬡</button>
      </n-dropdown>
    </div>
  </div>
</template>

<style scoped>
.header {
  height: 52px;
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #141413;
  border-bottom: 1px solid #30302e;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: #87867f;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.char-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  border-radius: 20px;
  border: 1px solid #30302e;
  cursor: pointer;
  transition: border-color 0.15s;
}
.char-pill:hover { border-color: #5e5d59; }
.char-pill.no-cursor { cursor: default; }
.char-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
}
.char-name { font-size: 0.85rem; color: #b0aea5; }
.caret { font-size: 0.65rem; color: #5e5d59; }
.icon-btn {
  background: none;
  border: 1px solid #30302e;
  color: #5e5d59;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s, color 0.15s;
}
.icon-btn:hover { border-color: #5e5d59; color: #b0aea5; }
.lang-btn {
  background: none;
  border: 1px solid #30302e;
  color: #87867f;
  padding: 0 10px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.03em;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: border-color 0.15s, color 0.15s;
}
.lang-btn:hover { border-color: #5e5d59; color: #b0aea5; }
.lang-btn .caret { font-size: 0.6rem; color: #5e5d59; }
.header-divider {
  color: #30302e;
  font-size: 0.75rem;
  user-select: none;
}
.header-copyright {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.04em;
  color: #5e5d59;
  text-decoration: none;
  transition: color 0.15s;
}
.header-copyright:hover { color: #b0aea5; }
</style>
