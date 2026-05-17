"""Bulk entity name resolution via ESI /universe/names/ with Redis-backed cache."""
import asyncio
import json
import logging
import time

import httpx
import redis.asyncio as aioredis

from app.core.redis import get_pool

logger = logging.getLogger(__name__)

ESI_NAMES_URL = "https://esi.evetech.net/latest/universe/names/"
_KEY_PREFIX = "esi:name:"
_LOGICAL_TTL = 86400   # 24h — 逻辑过期，超出后返回旧值并触发后台刷新
_HARD_TTL = 172800     # 48h — Redis key 真实 TTL，兜底防止永不淘汰


def _redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


async def _fetch_from_esi(ids: list[int]) -> dict[int, dict]:
    result: dict[int, dict] = {}
    chunks = [ids[i : i + 1000] for i in range(0, len(ids), 1000)]
    async with httpx.AsyncClient(timeout=15.0) as client:
        for chunk in chunks:
            try:
                resp = await client.post(ESI_NAMES_URL, json=chunk)
                if resp.status_code == 200:
                    for item in resp.json():
                        result[item["id"]] = {"name": item["name"], "category": item["category"]}
            except Exception as exc:
                logger.warning("ESI /universe/names/ request failed: %s", exc)
    return result


async def _refresh_ids(ids: list[int]) -> None:
    """后台任务：重新从 ESI 拉取并更新 Redis 缓存。"""
    fetched = await _fetch_from_esi(ids)
    if not fetched:
        return
    now = time.time()
    r = _redis()
    pipe = r.pipeline()
    for eid, data in fetched.items():
        payload = json.dumps({
            "name": data["name"],
            "category": data["category"],
            "expire_at": now + _LOGICAL_TTL,
        })
        pipe.set(f"{_KEY_PREFIX}{eid}", payload, ex=_HARD_TTL)
    await pipe.execute()
    await r.aclose()


async def resolve_entity_names(ids: list[int | None]) -> dict[int, dict]:
    """
    批量解析 entity ID → {name, category}。

    缓存策略（Redis）：
    - 命中且未逻辑过期 → 直接返回
    - 命中但逻辑已过期 → 立即返回旧数据，后台异步刷新
    - 未命中            → 同步请求 ESI，写入缓存后返回
    """
    valid_ids = list({i for i in ids if i is not None and i > 0})
    if not valid_ids:
        return {}

    r = _redis()
    now = time.time()
    result: dict[int, dict] = {}
    stale_ids: list[int] = []
    miss_ids: list[int] = []

    keys = [f"{_KEY_PREFIX}{i}" for i in valid_ids]
    values = await r.mget(keys)
    await r.aclose()

    for eid, raw in zip(valid_ids, values):
        if raw is None:
            miss_ids.append(eid)
            continue
        data = json.loads(raw)
        result[eid] = {"name": data["name"], "category": data["category"]}
        if data["expire_at"] < now:
            stale_ids.append(eid)

    if stale_ids:
        asyncio.create_task(_refresh_ids(stale_ids))

    if miss_ids:
        for eid in miss_ids:
            result[eid] = {"name": "正在初始化数据，请稍后再试", "category": "unknown"}
        asyncio.create_task(_refresh_ids(miss_ids))

    return result


async def enrich_entity_names(
    rows: list[dict],
    id_field: str,
    name_field: str,
    *,
    skip_types: set[str] | None = None,
    type_field: str | None = None,
) -> None:
    ids = []
    for row in rows:
        eid = row.get(id_field)
        if eid is None:
            continue
        if type_field and skip_types and row.get(type_field) in skip_types:
            continue
        ids.append(eid)

    name_map = await resolve_entity_names(ids)
    for row in rows:
        eid = row.get(id_field)
        if eid is not None and eid in name_map:
            row[name_field] = name_map[eid]["name"]
        else:
            row.setdefault(name_field, None)
