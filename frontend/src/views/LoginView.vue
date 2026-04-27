<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Helm</h1>
      <p class="subtitle">EVE Online 玩家管理工具</p>
      <button class="eve-btn" @click="auth.loginWithEve()">
        <img src="https://web.ccpgamescdn.com/eveonlineassets/developers/eve-sso-login-black-small.png" alt="Login with EVE Online" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0d1117;
}

.login-card {
  text-align: center;
  padding: 48px 64px;
  background: #161b22;
  border-radius: 12px;
  border: 1px solid #30363d;
}

h1 {
  font-size: 2.5rem;
  color: #c9d1d9;
  margin-bottom: 8px;
  letter-spacing: 4px;
}

.subtitle {
  color: #8b949e;
  margin-bottom: 32px;
  font-size: 0.95rem;
}

.eve-btn {
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.9;
  transition: opacity 0.2s;
}

.eve-btn:hover {
  opacity: 1;
}
</style>
