<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <span class="brand-mark">H</span><span class="brand-text">ELM</span>
      </div>
      <p class="subtitle">EVE Online 玩家管理工具</p>
      <div class="divider" />
      <p class="desc">使用你的 EVE Online 账号登录，绑定角色后即可开始使用。</p>
      <button class="eve-btn" @click="auth.loginWithEve()">
        <img
          src="https://web.ccpgamescdn.com/eveonlineassets/developers/eve-sso-login-black-small.png"
          alt="Login with EVE Online"
        />
      </button>
      <p class="fine-print">登录即表示你同意 EVE Online 服务条款</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #141413;
}

.login-card {
  text-align: center;
  padding: 48px 56px;
  background: #1e1e1c;
  border-radius: 12px;
  border: 1px solid #30302e;
  box-shadow: rgba(0,0,0,0.2) 0px 8px 32px;
  min-width: 340px;
}

.brand {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  margin-bottom: 10px;
}
.brand-mark {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 2rem;
  font-weight: 500;
  color: #c96442;
  line-height: 1;
}
.brand-text {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 2rem;
  font-weight: 500;
  color: #faf9f5;
  letter-spacing: 5px;
  line-height: 1;
}

.subtitle {
  color: #87867f;
  font-size: 0.9rem;
  margin-bottom: 0;
}

.divider {
  width: 40px;
  height: 1px;
  background: #30302e;
  margin: 24px auto;
}

.desc {
  color: #5e5d59;
  font-size: 0.85rem;
  line-height: 1.6;
  margin-bottom: 28px;
  max-width: 260px;
  margin-left: auto;
  margin-right: auto;
}

.eve-btn {
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.88;
  transition: opacity 0.18s;
  display: block;
  margin: 0 auto 20px;
}
.eve-btn:hover { opacity: 1; }

.fine-print {
  font-size: 0.72rem;
  color: #3d3d3a;
}
</style>
