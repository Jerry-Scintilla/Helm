<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()

interface Character {
  character_id: number
  character_name: string
}

const characters = ref<Character[]>([])

onMounted(async () => {
  try {
    const res = await api.get('/api/v1/characters/')
    characters.value = res.data
  } catch {}
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

const adminMenuOptions = computed(() => [
  { label: '系统', key: '/admin/system' },
  { label: '用户', key: '/admin/users' },
  { label: '角色权限', key: '/admin/roles' },
  { label: 'SDE', key: '/admin/sde' },
  { label: 'Buckets', key: '/admin/buckets' },
  { label: 'API Token', key: '/admin/tokens' },
  { label: '插件', key: '/admin/plugins' },
])

function handleAdminMenu(key: string) {
  router.push(key)
}

const userMenuOptions = [{ label: '退出登录', key: 'logout' }]

function handleUserMenu(key: string) {
  if (key === 'logout') handleLogout()
}
</script>

<template>
  <div class="header">
    <div class="header-left">
      <slot name="title" />
    </div>
    <div class="header-right">
      <!-- Admin menu (superuser only) -->
      <n-dropdown
        v-if="auth.isSuperuser"
        trigger="click"
        :options="adminMenuOptions"
        @select="handleAdminMenu"
      >
        <button class="icon-btn" title="管理后台">⚙</button>
      </n-dropdown>

      <!-- Character switcher -->
      <n-dropdown
        v-if="characters.length > 1"
        trigger="click"
        :options="characters.map(c => ({ label: c.character_name, key: c.character_id }))"
        @select="(k: number) => router.push(`/character/${k}/overview`)"
      >
        <div class="char-pill">
          <img
            v-if="auth.characterId"
            :src="`https://images.evetech.net/characters/${auth.characterId}/portrait?size=32`"
            class="char-avatar"
            alt=""
          />
          <span class="char-name">{{ auth.characterName }}</span>
          <span class="caret">▾</span>
        </div>
      </n-dropdown>

      <div v-else class="char-pill no-cursor">
        <img
          v-if="auth.characterId"
          :src="`https://images.evetech.net/characters/${auth.characterId}/portrait?size=32`"
          class="char-avatar"
          alt=""
        />
        <span class="char-name">{{ auth.characterName }}</span>
      </div>

      <!-- User menu -->
      <n-dropdown trigger="click" :options="userMenuOptions" @select="handleUserMenu">
        <button class="icon-btn" title="用户菜单">⬡</button>
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
</style>
