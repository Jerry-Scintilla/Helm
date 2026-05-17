<script setup lang="ts">
import { ref } from 'vue'
import { resolveSdeName } from '@/utils/sde'
import type { SdeName } from '@/utils/sde'
import AssetItemGroup from './AssetItemGroup.vue'

export interface AssetNode {
  item_id: number
  type_id: number
  type_name?: SdeName | null
  icon_url?: string | null
  quantity: number
  is_singleton: boolean
  items: AssetNode[]
}

const props = defineProps<{
  items: AssetNode[]
  depth?: number
}>()

const openSet = ref<Set<number>>(new Set())

function toggle(itemId: number) {
  if (openSet.value.has(itemId)) {
    openSet.value.delete(itemId)
  } else {
    openSet.value.add(itemId)
  }
}

function countAll(nodes: AssetNode[]): number {
  return nodes.reduce((n, node) => n + 1 + countAll(node.items), 0)
}

const depth = props.depth ?? 0
</script>

<template>
  <div class="item-group">
    <template v-for="node in items" :key="node.item_id">

      <!-- Container / ship: custom disclosure row -->
      <template v-if="node.items.length > 0">
        <div
          class="asset-row container-row"
          :class="`indent-${Math.min(depth, 4)}`"
          @click="toggle(node.item_id)"
        >
          <span class="container-name">
            <img v-if="node.icon_url" :src="node.icon_url" class="type-icon" width="24" height="24" alt="" loading="lazy" @error="(e) => ((e.target as HTMLImageElement).style.display = 'none')" />
            {{ resolveSdeName(node.type_name, String(node.type_id)) }}
          </span>
          <span class="container-meta">
            <span class="container-count">{{ countAll(node.items) }} 项</span>
            <span class="container-arrow" :class="{ open: openSet.has(node.item_id) }">›</span>
          </span>
        </div>
        <div v-if="openSet.has(node.item_id)" class="children">
          <AssetItemGroup :items="node.items" :depth="depth + 1" />
        </div>
      </template>

      <!-- Leaf item -->
      <div v-else class="asset-row" :class="`indent-${Math.min(depth, 4)}`">
        <span class="type-name">
          <img v-if="node.icon_url" :src="node.icon_url" class="type-icon" width="24" height="24" alt="" loading="lazy" />
          {{ resolveSdeName(node.type_name, String(node.type_id)) }}
        </span>
        <span class="qty">{{ node.is_singleton ? '1' : node.quantity }}</span>
      </div>

    </template>
  </div>
</template>

<style scoped>
.item-group {
  width: 100%;
}

/* All rows share the same grid — containers and leaves align exactly */
.asset-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  padding: 6px 12px;
  font-size: 0.85rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  align-items: center;
}

/* Leaf indentation for nested levels */
.asset-row.indent-1 { padding-left: 28px; }
.asset-row.indent-2 { padding-left: 44px; }
.asset-row.indent-3 { padding-left: 60px; }
.asset-row.indent-4 { padding-left: 76px; }

/* Item icon */
.type-icon {
  width: 24px;
  height: 24px;
  border-radius: 2px;
  flex-shrink: 0;
  margin-right: 6px;
  vertical-align: middle;
}

/* Leaf text */
.type-name {
  display: flex;
  align-items: center;
  color: #faf9f5;
}
.qty {
  color: #87867f;
  text-align: right;
  min-width: 40px;
}

/* Container row */
.container-row {
  cursor: pointer;
  user-select: none;
}
.container-row:hover {
  background: rgba(255, 255, 255, 0.03);
}
.container-name {
  display: flex;
  align-items: center;
  color: #d97757; /* Coral Accent */
}
.container-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}
.container-count {
  font-size: 0.75rem;
  color: #5e5d59;
}
.container-arrow {
  font-size: 1rem;
  color: #5e5d59;
  display: inline-block;
  transition: transform 0.15s ease;
  transform: rotate(0deg);
  line-height: 1;
}
.container-arrow.open {
  transform: rotate(90deg);
}

.children {
  border-left: 1px solid #30302e;
  margin-left: 12px;
}
</style>
