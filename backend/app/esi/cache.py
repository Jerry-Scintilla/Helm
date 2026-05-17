import json
import re
import time
from dataclasses import dataclass
from typing import Any

import redis.asyncio as aioredis

from app.core.redis import get_pool

# Keys matching these patterns are stored with logical expiry only — no Redis physical TTL.
_NO_PHYSICAL_TTL_PATTERNS: list[re.Pattern] = [
    re.compile(r"^/characters/\d+/portrait/"),
]


def _get_client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


@dataclass
class CachedEntry:
    data: Any
    etag: str | None
    is_stale: bool
    ttl_remaining: int


async def get_cached(key: str) -> CachedEntry | None:
    """
    Return CachedEntry or None if not cached.
    Uses logical expiration (stored_at + ttl) instead of Redis TTL.
    """
    client = _get_client()
    try:
        raw = await client.hgetall(f"esi:cache:{key}")
        if not raw:
            return None

        data = json.loads(raw["data"])
        etag = raw.get("etag")
        stored_at = float(raw["stored_at"])
        ttl = int(raw.get("ttl", 300))

        now = time.time()
        age = now - stored_at
        is_stale = age > ttl
        ttl_remaining = max(0, int(ttl - age))

        return CachedEntry(data=data, etag=etag, is_stale=is_stale, ttl_remaining=ttl_remaining)
    finally:
        await client.aclose()


async def set_cached(key: str, data: Any, ttl: int, etag: str | None = None) -> None:
    """
    Store data in Redis Hash with logical expiration metadata.
    Redis key expiry is set to 2x TTL (physical backup expiry).
    """
    client = _get_client()
    try:
        mapping = {
            "data": json.dumps(data),
            "etag": etag or "",
            "stored_at": str(time.time()),
            "ttl": str(ttl),
        }
        await client.hset(f"esi:cache:{key}", mapping=mapping)
        if not any(p.match(key) for p in _NO_PHYSICAL_TTL_PATTERNS):
            physical_ttl = max(ttl * 2, 86400)
            await client.expire(f"esi:cache:{key}", physical_ttl)
    finally:
        await client.aclose()


async def get_cached_pages(key: str) -> tuple[list[Any], str | None, bool, int]:
    """
    Return (pages, etag, is_stale, ttl_remaining) for paginated endpoints.
    """
    client = _get_client()
    try:
        raw = await client.hgetall(f"esi:cache:{key}")
        if not raw:
            return [], None, False, 0

        pages = []
        for field, value in raw.items():
            if field.startswith("page_"):
                pages.append((int(field.split("_")[1]), json.loads(value)))

        pages.sort(key=lambda x: x[0])
        sorted_pages = [p[1] for p in pages]

        etag = raw.get("etag")
        stored_at = float(raw["stored_at"])
        ttl = int(raw.get("ttl", 300))

        now = time.time()
        age = now - stored_at
        is_stale = age > ttl
        ttl_remaining = max(0, int(ttl - age))

        return sorted_pages, etag, is_stale, ttl_remaining
    finally:
        await client.aclose()


async def set_cached_pages(
    key: str, pages: list[Any], ttl: int, etag: str | None = None
) -> None:
    """
    Store paginated data in Redis Hash.
    Stores both aggregated 'data' and individual 'page_N' fields.
    """
    client = _get_client()
    try:
        mapping = {
            "data": json.dumps(pages),
            "etag": etag or "",
            "stored_at": str(time.time()),
            "ttl": str(ttl),
        }
        for i, page_data in enumerate(pages, 1):
            mapping[f"page_{i}"] = json.dumps(page_data)

        await client.hset(f"esi:cache:{key}", mapping=mapping)
        physical_ttl = max(ttl * 2, 86400)
        await client.expire(f"esi:cache:{key}", physical_ttl)
    finally:
        await client.aclose()


async def acquire_refresh_lock(key: str, ttl: int = 60) -> bool:
    """Try to acquire a refresh lock. Returns True if acquired."""
    client = _get_client()
    try:
        lock_key = f"esi:refresh:lock:{key}"
        acquired = await client.set(lock_key, "1", nx=True, ex=ttl)
        return bool(acquired)
    finally:
        await client.aclose()


async def release_refresh_lock(key: str) -> None:
    """Release the refresh lock for a cache key."""
    client = _get_client()
    try:
        await client.delete(f"esi:refresh:lock:{key}")
    finally:
        await client.aclose()


TTL_CONFIG: dict[str, int] = {
    "/markets/{id}/orders/": 300,
    "/markets/prices/": 3600,
    "/characters/{id}/affiliation/": 7200,
    "/characters/{id}/": 600,
    "/characters/{id}/skills/": 7200,
    "/characters/{id}/skillqueue/": 3600,
    "/characters/{id}/assets/": 3600,
    "/characters/{id}/wallet/": 1800,
    "/characters/{id}/wallet/transactions/": 1800,
    "/characters/{id}/wallet/journal/": 1800,
    "/characters/{id}/mail/": 900,
    "/characters/{id}/portrait/": 3600,
    "/characters/{id}/notifications/": 900,
    "/characters/{id}/contracts/": 3600,
    "/corporations/{id}/": 7200,
    "/corporations/{id}/members/": 3600,
    "/corporations/{id}/wallets/": 1800,
    "/corporations/{id}/assets/": 3600,
    "/alliances/{id}/": 86400,
    "/alliances/{id}/corporations/": 86400,
    "default": 300,
}


def get_ttl_for_path(path: str) -> int:
    """Return the configured TTL for a given ESI path.

    Matches against patterns with '{id}' placeholder, e.g.:
        '/characters/123/skills/' matches '/characters/{id}/skills/'
    """
    # Exact match first
    if path in TTL_CONFIG:
        return TTL_CONFIG[path]

    # Pattern match: try replacing numeric IDs with {id}
    import re
    normalized = re.sub(r'/\d+/', '/{id}/', path)
    if normalized in TTL_CONFIG:
        return TTL_CONFIG[normalized]

    return TTL_CONFIG["default"]