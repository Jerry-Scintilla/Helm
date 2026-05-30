<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore, type Killmail, type KillmailDetail } from '@/stores/character'
import { useI18n } from 'vue-i18n'
import type { DataTableColumns } from 'naive-ui'
import { NTag } from 'naive-ui'
import HelmLoader from '@/components/HelmLoader.vue'

const route = useRoute()
const charStore = useCharacterStore()
const { t, locale } = useI18n()
const characterId = Number(route.params.id)

const loading = ref(true)
const rows = ref<Killmail[]>([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const filter = ref<'all' | 'kills' | 'losses'>('all')

const showDetail = ref(false)
const detailLoading = ref(false)
const detail = ref<KillmailDetail | null>(null)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await charStore.fetchKillmails(characterId, { filter: filter.value, page: page.value })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function changeFilter(f: 'all' | 'kills' | 'losses') {
  if (filter.value === f) return
  filter.value = f
  page.value = 1
  load()
}

function changePage(delta: number) {
  const next = page.value + delta
  if (next < 1 || (next - 1) * perPage >= total.value) return
  page.value = next
  load()
}

async function openDetail(killmailId: number) {
  showDetail.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await charStore.fetchKillmailDetail(characterId, killmailId, locale.value)
  } finally {
    detailLoading.value = false
  }
}

function fmtIsk(n: number | null): string {
  if (!n) return '—'
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(2) + 'K'
  return n.toFixed(0)
}
function fmtDate(dt: string | null): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleString()
}

const cols: DataTableColumns<Killmail> = [
  { title: () => t('killboard.time'), key: 'killmail_time', width: 160, render: r => fmtDate(r.killmail_time) },
  {
    title: () => t('killboard.result'), key: 'is_loss', width: 80,
    render: r => h(NTag, { size: 'small', type: r.is_loss ? 'error' : 'success', bordered: false },
      { default: () => (r.is_loss ? t('killboard.loss') : t('killboard.kill')) }),
  },
  {
    title: () => t('killboard.ship'), key: 'ship_name', ellipsis: true,
    render: r => h('div', { style: 'display:flex;align-items:center;gap:8px' }, [
      r.ship_icon ? h('img', { src: r.ship_icon, style: 'width:28px;height:28px;border-radius:4px' }) : null,
      h('span', r.ship_name || `#${r.ship_type_id ?? '?'}`),
    ]),
  },
  { title: () => t('killboard.system'), key: 'solar_system_name', width: 130, render: r => r.solar_system_name || '—' },
  { title: () => t('killboard.value'), key: 'total_value', width: 110, align: 'right', render: r => fmtIsk(r.total_value) },
  { title: () => t('killboard.involved'), key: 'attacker_count', width: 80, align: 'right' },
]

function rowProps(row: Killmail) {
  return { style: 'cursor: pointer', onClick: () => openDetail(row.killmail_id) }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title h-serif">{{ t('nav.killboard') }}</h1>
      <n-button-group size="small">
        <n-button :type="filter === 'all' ? 'primary' : 'default'" @click="changeFilter('all')">{{ t('killboard.filter.all') }}</n-button>
        <n-button :type="filter === 'kills' ? 'primary' : 'default'" @click="changeFilter('kills')">{{ t('killboard.filter.kills') }}</n-button>
        <n-button :type="filter === 'losses' ? 'primary' : 'default'" @click="changeFilter('losses')">{{ t('killboard.filter.losses') }}</n-button>
      </n-button-group>
    </div>

    <div v-if="loading" class="helm-section-loader"><HelmLoader :size="36" /></div>
    <template v-else>
      <n-data-table
        :columns="cols"
        :data="rows"
        :bordered="false"
        size="small"
        :row-key="(r: Killmail) => r.killmail_id"
        :row-props="rowProps"
      />
      <div v-if="rows.length === 0" class="muted">{{ t('killboard.empty') }}</div>
      <div class="pagination">
        <n-button size="small" :disabled="page <= 1" @click="changePage(-1)">{{ t('common.prevPage') }}</n-button>
        <span class="page-num">{{ t('common.page', { n: page }) }} · {{ total }}</span>
        <n-button size="small" :disabled="page * perPage >= total" @click="changePage(1)">{{ t('common.nextPage') }}</n-button>
      </div>
    </template>

    <!-- Detail drawer -->
    <n-drawer v-model:show="showDetail" :width="480" placement="right">
      <n-drawer-content :title="detail?.victim?.ship_name || t('killboard.victim')" closable>
        <div v-if="detailLoading" class="helm-section-loader"><HelmLoader :size="32" /></div>
        <template v-else-if="detail">
          <!-- Victim -->
          <div class="victim-card">
            <img v-if="detail.victim.ship_render" :src="detail.victim.ship_render" class="victim-render" alt="" />
            <div class="victim-info">
              <div class="victim-name">{{ detail.victim.character_name || '—' }}</div>
              <div class="victim-sub">{{ detail.victim.corporation_name || '' }}<template v-if="detail.victim.alliance_name"> / {{ detail.victim.alliance_name }}</template></div>
              <div class="victim-sub">{{ detail.victim.ship_name }} · {{ detail.solar_system_name || '—' }}</div>
              <div class="victim-value">{{ fmtIsk(detail.total_value) }} ISK</div>
            </div>
          </div>
          <div class="meta-row">
            <span>{{ t('killboard.time') }}: {{ fmtDate(detail.killmail_time) }}</span>
            <span>{{ t('killboard.damageTaken') }}: {{ detail.victim.damage_taken.toLocaleString() }}</span>
          </div>

          <!-- Attackers -->
          <div class="d-section-title">{{ t('killboard.attackers') }} ({{ detail.attackers.length }})</div>
          <div v-for="(a, i) in detail.attackers" :key="i" class="atk" :class="{ fb: a.final_blow }">
            <img v-if="a.ship_icon" :src="a.ship_icon" class="atk-icon" alt="" />
            <div class="atk-main">
              <div class="atk-name">
                {{ a.character_name || a.corporation_name || '—' }}
                <span v-if="a.final_blow" class="fb-tag">{{ t('killboard.finalBlow') }}</span>
              </div>
              <div class="atk-sub">{{ a.ship_name || '' }}<template v-if="a.weapon_name"> · {{ a.weapon_name }}</template></div>
            </div>
            <span class="atk-dmg">{{ a.damage_done.toLocaleString() }}</span>
          </div>

          <!-- Items -->
          <div v-if="detail.victim.items.length" class="d-section-title">{{ t('killboard.items') }}</div>
          <div v-for="(it, i) in detail.victim.items" :key="'i' + i" class="kitem">
            <img v-if="it.icon_url" :src="it.icon_url" class="kitem-icon" alt="" />
            <span class="kitem-name">{{ it.type_name }}</span>
            <span v-if="it.dropped" class="kitem-drop">{{ t('killboard.dropped') }} {{ it.dropped.toLocaleString() }}</span>
            <span v-if="it.destroyed" class="kitem-dest">{{ t('killboard.destroyed') }} {{ it.destroyed.toLocaleString() }}</span>
          </div>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 1.6rem; color: #faf9f5; margin: 0; }
.muted { padding: 24px 4px; color: #5e5d59; font-size: 0.9rem; }
.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.page-num { font-size: 0.85rem; color: #87867f; }

.victim-card { display: flex; gap: 12px; align-items: center; }
.victim-render { width: 96px; height: 96px; border-radius: 8px; flex-shrink: 0; background: #141413; }
.victim-info { min-width: 0; }
.victim-name { font-size: 1rem; color: #faf9f5; font-weight: 500; }
.victim-sub { font-size: 0.8rem; color: #87867f; margin-top: 2px; }
.victim-value { font-size: 0.9rem; color: #d97757; margin-top: 6px; }
.meta-row { display: flex; justify-content: space-between; font-size: 0.78rem; color: #87867f; margin: 12px 0; padding-bottom: 12px; border-bottom: 1px solid #2a2a28; }

.d-section-title { font-size: 0.8rem; color: #87867f; margin: 16px 0 8px; }
.atk { display: flex; align-items: center; gap: 8px; padding: 5px 0; }
.atk.fb { background: rgba(217,119,87,0.08); border-radius: 6px; padding-left: 6px; }
.atk-icon { width: 28px; height: 28px; border-radius: 4px; flex-shrink: 0; }
.atk-main { flex: 1; min-width: 0; }
.atk-name { font-size: 0.85rem; color: #b0aea5; }
.fb-tag { font-size: 0.65rem; color: #d97757; border: 1px solid #d97757; border-radius: 3px; padding: 0 4px; margin-left: 6px; }
.atk-sub { font-size: 0.72rem; color: #5e5d59; }
.atk-dmg { font-size: 0.8rem; color: #87867f; }

.kitem { display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: #b0aea5; padding: 3px 0; }
.kitem-icon { width: 22px; height: 22px; border-radius: 3px; }
.kitem-name { flex: 1; }
.kitem-drop { font-size: 0.72rem; color: #6abf69; }
.kitem-dest { font-size: 0.72rem; color: #5e5d59; }
</style>
