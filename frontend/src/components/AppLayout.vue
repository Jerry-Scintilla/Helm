<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
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
      <div class="shell-content">
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
</style>
