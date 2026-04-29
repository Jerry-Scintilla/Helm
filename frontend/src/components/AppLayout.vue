<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import { usePluginStore } from '@/stores/plugin'

const pluginStore = usePluginStore()
onMounted(() => { pluginStore.fetchEnabledPlugins() })

const route = useRoute()
const isIframeRoute = computed(() => route.meta.iframePlugin === true)
</script>

<template>
  <div class="shell">
    <AppSidebar />
    <div class="shell-right">
      <AppHeader>
        <template #title>
          <slot name="header-title" />
        </template>
      </AppHeader>
      <div class="shell-content" :class="{ 'shell-content--iframe': isIframeRoute }">
        <RouterView />
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #141413;
}

.shell-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.shell-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px 28px;
  scrollbar-width: thin;
  scrollbar-color: #30302e #141413;
}

.shell-content--iframe {
  padding: 0;
  overflow: hidden;
}
</style>
