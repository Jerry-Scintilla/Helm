import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

const TTL_MS = 3_600_000 // 1 hour — matches backend logical expiry

interface PortraitData {
  px64x64: string
  px128x128: string
  px256x256: string
  px512x512: string
}

interface CacheEntry {
  data: PortraitData
  stored_at: number
}

function readStorage(id: number): CacheEntry | null {
  try {
    const raw = localStorage.getItem(`portrait:${id}`)
    return raw ? (JSON.parse(raw) as CacheEntry) : null
  } catch {
    return null
  }
}

function writeStorage(id: number, entry: CacheEntry) {
  try {
    localStorage.setItem(`portrait:${id}`, JSON.stringify(entry))
  } catch {}
}

export const usePortraitStore = defineStore('portrait', () => {
  const portraits = ref<Map<number, PortraitData>>(new Map())
  const refreshing = new Set<number>()

  function _hydrate(id: number): CacheEntry | null {
    if (portraits.value.has(id)) return null // already in memory
    const entry = readStorage(id)
    if (entry) portraits.value.set(id, entry.data)
    return entry
  }

  async function _doFetch(id: number) {
    if (refreshing.has(id)) return
    refreshing.add(id)
    try {
      const res = await api.get<PortraitData>(`/api/v1/characters/${id}/portrait`)
      const entry: CacheEntry = { data: res.data, stored_at: Date.now() }
      portraits.value.set(id, res.data)
      writeStorage(id, entry)
    } catch {
      // keep stale data on failure
    } finally {
      refreshing.delete(id)
    }
  }

  // Stale-while-revalidate: returns immediately (stale or fallback), refreshes in background
  function fetchPortrait(id: number) {
    if (!id) return

    // Already in memory — check localStorage for freshness
    if (portraits.value.has(id)) {
      const stored = readStorage(id)
      if (!stored || Date.now() - stored.stored_at > TTL_MS) {
        _doFetch(id)
      }
      return
    }

    const entry = _hydrate(id)
    if (!entry) {
      // Cache miss — fetch synchronously so reactive ref populates
      _doFetch(id)
      return
    }

    if (Date.now() - entry.stored_at > TTL_MS) {
      // Stale — data already loaded into memory, refresh quietly in background
      _doFetch(id)
    }
  }

  function getUrl(id: number, size: 32 | 64 | 128 | 256 | 512 = 128): string {
    const data = portraits.value.get(id)
    if (!data) return `https://images.evetech.net/characters/${id}/portrait?size=${size}`
    if (size <= 64) return data.px64x64
    if (size <= 128) return data.px128x128
    if (size <= 256) return data.px256x256
    return data.px512x512
  }

  return { portraits, fetchPortrait, getUrl }
})
