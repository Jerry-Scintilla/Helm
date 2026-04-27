import json
from typing import Any

import redis.asyncio as aioredis

from app.core.redis import get_pool


def _get_client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


async def get_cached(key: str) -> tuple[Any | None, str | None]:
    """Return (data, etag) or (None, None) if not cached."""
    client = _get_client()
    try:
        raw = await client.get(f"esi:cache:{key}")
        if raw is None:
            return None, None
        entry = json.loads(raw)
        return entry.get("data"), entry.get("etag")
    finally:
        await client.aclose()


async def set_cached(key: str, data: Any, ttl: int, etag: str | None = None) -> None:
    client = _get_client()
    try:
        entry = {"data": data, "etag": etag}
        await client.setex(f"esi:cache:{key}", ttl, json.dumps(entry))
    finally:
        await client.aclose()
