import json
import time
from typing import Any

import redis.asyncio as aioredis

from app.core.redis import get_pool

WALLET_TTL = 1800  # 30 minutes — matches ESI cache TTL for wallet endpoints


def _client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


async def logical_get(key: str) -> tuple[Any | None, bool]:
    """
    Returns (data, is_stale).
      data=None, is_stale=False  → cache miss
      data=...,  is_stale=False  → fresh hit
      data=...,  is_stale=True   → stale hit: return data, trigger background refresh
    """
    client = _client()
    try:
        raw = await client.get(key)
        if raw is None:
            return None, False
        entry = json.loads(raw)
        return entry["data"], time.time() > entry["expire_at"]
    finally:
        await client.aclose()


async def logical_set(key: str, data: Any, ttl: int) -> None:
    """Store with embedded expire_at. Physical Redis TTL = 3× logical TTL."""
    client = _client()
    try:
        entry = {"data": data, "expire_at": time.time() + ttl}
        await client.set(key, json.dumps(entry, default=str), ex=ttl * 3)
    finally:
        await client.aclose()


async def logical_delete(key: str) -> None:
    client = _client()
    try:
        await client.delete(key)
    finally:
        await client.aclose()


async def delete_prefix(prefix: str) -> int:
    """Delete every key starting with `prefix`. Returns the count removed.

    Used to invalidate a family of derived-response cache entries (e.g. all
    paginated list pages for one entity) after a background sync writes fresh
    rows to the DB, so the next read rebuilds the cache from the new data.
    """
    client = _client()
    deleted = 0
    try:
        async for key in client.scan_iter(match=f"{prefix}*", count=200):
            await client.delete(key)
            deleted += 1
        return deleted
    finally:
        await client.aclose()


async def try_acquire_lock(key: str, ttl: int = 30) -> bool:
    """Distributed lock to prevent cache stampede. Returns True if acquired."""
    client = _client()
    try:
        return bool(await client.set(f"lock:{key}", "1", nx=True, ex=ttl))
    finally:
        await client.aclose()
