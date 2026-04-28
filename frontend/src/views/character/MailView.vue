<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '@/stores/character'

const route = useRoute()
const charStore = useCharacterStore()
const characterId = Number(route.params.id)
const loading = ref(true)
const loadingBody = ref(false)

onMounted(async () => {
  try {
    await charStore.fetchMails(characterId)
  } finally {
    loading.value = false
  }
})

async function openMail(mailId: number) {
  loadingBody.value = true
  try {
    await charStore.fetchMailBody(characterId, mailId)
  } finally {
    loadingBody.value = false
  }
}

function fmtDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('zh-CN')
}
</script>

<template>
  <div>
    <h1 class="page-title h-serif">邮件</h1>

    <n-spin v-if="loading" :size="24" style="display:block;margin:60px auto;" />
    <div v-else class="mail-layout">
      <!-- Mail list -->
      <div class="mail-list">
        <div
          v-for="mail in charStore.mails"
          :key="mail.mail_id"
          class="mail-item"
          :class="{ unread: !mail.is_read, active: charStore.selectedMail?.mail_id === mail.mail_id }"
          @click="openMail(mail.mail_id)"
        >
          <div class="mail-subject">{{ mail.subject || '(无标题)' }}</div>
          <div class="mail-meta">
            <span>From {{ mail.from_name ?? mail.from_id ?? '?' }}</span>
            <span>{{ fmtDate(mail.timestamp) }}</span>
          </div>
        </div>
        <div v-if="charStore.mails.length === 0" class="muted">暂无邮件</div>
      </div>

      <!-- Mail detail -->
      <div class="mail-detail">
        <n-spin v-if="loadingBody" :size="20" style="margin:40px auto;display:block;" />
        <div v-else-if="charStore.selectedMail" class="mail-body-wrap">
          <h2 class="detail-subject">{{ charStore.selectedMail.subject || '(无标题)' }}</h2>
          <div class="detail-meta">
            <span>发件人 {{ charStore.selectedMail.from_name ?? charStore.selectedMail.from_id ?? '?' }}</span>
            <span>{{ fmtDate(charStore.selectedMail.timestamp) }}</span>
          </div>
          <div class="detail-body">{{ charStore.selectedMail.body }}</div>
        </div>
        <div v-else class="no-selection">← 点击左侧邮件查看内容</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.6rem; color: #faf9f5; margin-bottom: 20px; }

.mail-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  height: calc(100vh - 180px);
}

.mail-list {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  overflow-y: auto;
}
.mail-item {
  padding: 12px 16px;
  border-bottom: 1px solid #30302e;
  cursor: pointer;
  transition: background 0.15s;
}
.mail-item:hover { background: #252523; }
.mail-item.active { background: rgba(201,100,66,0.1); border-left: 2px solid #c96442; }
.mail-item.unread .mail-subject { color: #faf9f5; font-weight: 500; }
.mail-subject { font-size: 0.88rem; color: #b0aea5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mail-meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: #5e5d59; margin-top: 4px; }
.muted { padding: 24px 16px; color: #5e5d59; font-size: 0.9rem; }

.mail-detail {
  background: #1e1e1c;
  border: 1px solid #30302e;
  border-radius: 8px;
  padding: 20px 24px;
  overflow-y: auto;
}
.no-selection { color: #5e5d59; font-size: 0.9rem; }
.detail-subject { font-size: 1.1rem; font-weight: 500; color: #faf9f5; margin-bottom: 8px; }
.detail-meta { display: flex; gap: 16px; font-size: 0.8rem; color: #87867f; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #30302e; }
.detail-body { font-size: 0.9rem; color: #b0aea5; line-height: 1.7; white-space: pre-wrap; }
</style>
