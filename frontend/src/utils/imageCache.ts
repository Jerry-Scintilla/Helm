/**
 * IndexedDB-backed binary image cache.
 *
 * - Single object store keyed by absolute URL; each row stores the Blob plus
 *   size/last_access for LRU eviction.
 * - 100MB soft cap; on every successful write we check total bytes and evict
 *   least-recently-accessed rows until under the cap.
 * - In-memory map of object URLs so repeated lookups of the same URL share a
 *   single `createObjectURL` handle (revoked when the entry is evicted).
 * - Concurrent fetches for the same URL are deduped via an inflight promise
 *   map.
 *
 * Public API: getCachedImageUrl(src) → Promise<string>. Returns either the
 * cached object URL or, on cache failure, the original src so the browser can
 * still load it directly.
 */

const DB_NAME = 'helm-image-cache'
const DB_VERSION = 1
const STORE = 'images'
const MAX_BYTES = 100 * 1024 * 1024 // 100 MB
const EVICT_TARGET_BYTES = 90 * 1024 * 1024 // evict down to 90MB to avoid thrashing

interface CacheRow {
  url: string
  blob: Blob
  size: number
  stored_at: number
  last_access: number
}

let dbPromise: Promise<IDBDatabase> | null = null

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: 'url' })
        store.createIndex('last_access', 'last_access')
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
  return dbPromise
}

function promisifyRequest<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function dbGet(url: string): Promise<CacheRow | undefined> {
  const db = await openDB()
  const tx = db.transaction(STORE, 'readonly')
  return promisifyRequest(tx.objectStore(STORE).get(url) as IDBRequest<CacheRow | undefined>)
}

async function dbPut(row: CacheRow): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(STORE, 'readwrite')
  tx.objectStore(STORE).put(row)
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

async function dbTouch(url: string): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(STORE, 'readwrite')
  const store = tx.objectStore(STORE)
  const row = (await promisifyRequest(store.get(url))) as CacheRow | undefined
  if (row) {
    row.last_access = Date.now()
    store.put(row)
  }
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

// ── LRU eviction ─────────────────────────────────────────────────────────────

let evictPromise: Promise<void> | null = null

async function evictIfOverCap(): Promise<void> {
  if (evictPromise) return evictPromise
  evictPromise = (async () => {
    try {
      const db = await openDB()
      const tx = db.transaction(STORE, 'readwrite')
      const store = tx.objectStore(STORE)
      // First pass: tally total size.
      let total = 0
      await new Promise<void>((resolve, reject) => {
        const req = store.openCursor()
        req.onsuccess = () => {
          const cur = req.result
          if (cur) {
            total += (cur.value as CacheRow).size
            cur.continue()
          } else {
            resolve()
          }
        }
        req.onerror = () => reject(req.error)
      })
      if (total <= MAX_BYTES) return

      // Second pass: walk last_access index ascending, delete until under target.
      const idx = store.index('last_access')
      await new Promise<void>((resolve, reject) => {
        const req = idx.openCursor()
        req.onsuccess = () => {
          const cur = req.result
          if (!cur || total <= EVICT_TARGET_BYTES) {
            resolve()
            return
          }
          const row = cur.value as CacheRow
          total -= row.size
          // Revoke the in-memory object URL so the browser can free the Blob.
          const handle = objectUrls.get(row.url)
          if (handle) {
            URL.revokeObjectURL(handle)
            objectUrls.delete(row.url)
          }
          cur.delete()
          cur.continue()
        }
        req.onerror = () => reject(req.error)
      })
      await new Promise<void>((resolve, reject) => {
        tx.oncomplete = () => resolve()
        tx.onerror = () => reject(tx.error)
      })
    } catch {
      // Eviction failure is non-fatal — leave cache as is.
    } finally {
      evictPromise = null
    }
  })()
  return evictPromise
}

// ── Fetch + cache ────────────────────────────────────────────────────────────

const objectUrls = new Map<string, string>()
const inflight = new Map<string, Promise<string>>()

function blobToObjectUrl(url: string, blob: Blob): string {
  const existing = objectUrls.get(url)
  if (existing) return existing
  const obj = URL.createObjectURL(blob)
  objectUrls.set(url, obj)
  return obj
}

async function fetchAndCache(url: string): Promise<string> {
  // `mode: cors` so we get a usable Blob; `cache: default` lets browser cache
  // also help. Credentials omitted — CDN/icon endpoints don't need cookies.
  const res = await fetch(url, { mode: 'cors', credentials: 'omit' })
  if (!res.ok) throw new Error(`fetch failed: ${res.status}`)
  const blob = await res.blob()
  const now = Date.now()
  await dbPut({ url, blob, size: blob.size, stored_at: now, last_access: now })
  // Fire-and-forget eviction; never block the caller.
  void evictIfOverCap()
  return blobToObjectUrl(url, blob)
}

/**
 * Resolve a URL to a usable image src. Returns a cached object URL when
 * available, fetches and caches otherwise. On any cache/IO failure falls
 * back to the original URL so the <img> still works.
 */
export async function getCachedImageUrl(url: string): Promise<string> {
  if (!url) return url
  // Don't try to cache data: / blob: URLs.
  if (url.startsWith('data:') || url.startsWith('blob:')) return url

  // In-memory hot path.
  const cachedObj = objectUrls.get(url)
  if (cachedObj) {
    // Touch async; no need to await.
    void dbTouch(url)
    return cachedObj
  }

  // Dedupe concurrent loads of the same URL.
  const pending = inflight.get(url)
  if (pending) return pending

  const p = (async () => {
    try {
      const row = await dbGet(url)
      if (row) {
        void dbTouch(url)
        return blobToObjectUrl(url, row.blob)
      }
      return await fetchAndCache(url)
    } catch {
      // Fall back to the network URL directly; <img> will load it normally.
      return url
    } finally {
      inflight.delete(url)
    }
  })()
  inflight.set(url, p)
  return p
}

/**
 * Drop everything. Useful for debugging or a "clear cache" admin action.
 */
export async function clearImageCache(): Promise<void> {
  for (const handle of objectUrls.values()) URL.revokeObjectURL(handle)
  objectUrls.clear()
  inflight.clear()
  const db = await openDB()
  const tx = db.transaction(STORE, 'readwrite')
  tx.objectStore(STORE).clear()
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}
