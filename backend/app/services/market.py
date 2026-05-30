"""Lazy-load market price service with per-type Redis cache."""
import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.redis import get_pool
from app.esi.client import get_esi_client

logger = logging.getLogger(__name__)

_REGION_CONFIG_KEY = "market:config:region_id"
_PRICE_KEY_PREFIX = "market:price"


@dataclass
class MarketPrice:
    type_id: int
    region_id: int
    best_buy: float | None
    best_sell: float | None
    cached_at: float


def _price_key(region_id: int, type_id: int) -> str:
    return f"{_PRICE_KEY_PREFIX}:{region_id}:{type_id}"


def _get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


async def get_configured_region_id() -> int:
    client = _get_redis()
    try:
        val = await client.get(_REGION_CONFIG_KEY)
        return int(val) if val else settings.market_default_region_id
    finally:
        await client.aclose()


async def set_configured_region_id(region_id: int) -> None:
    client = _get_redis()
    try:
        await client.set(_REGION_CONFIG_KEY, str(region_id))
    finally:
        await client.aclose()


async def _get_cached_price(region_id: int, type_id: int) -> MarketPrice | None:
    client = _get_redis()
    try:
        raw = await client.get(_price_key(region_id, type_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return MarketPrice(**data)
    finally:
        await client.aclose()


async def _set_cached_price(price: MarketPrice) -> None:
    client = _get_redis()
    try:
        key = _price_key(price.region_id, price.type_id)
        await client.set(key, json.dumps(asdict(price)), ex=settings.market_price_ttl)
    finally:
        await client.aclose()


async def _fetch_price_from_esi(region_id: int, type_id: int) -> MarketPrice:
    esi = get_esi_client()
    try:
        orders = await esi.get(
            f"/markets/{region_id}/orders/",
            params={"type_id": str(type_id), "order_type": "all"},
            paginate=True,
        )
    except Exception:
        logger.exception("ESI market fetch failed region=%d type=%d", region_id, type_id)
        orders = []

    best_buy: float | None = None
    best_sell: float | None = None

    if orders:
        buy_prices = [o["price"] for o in orders if o.get("is_buy_order")]
        sell_prices = [o["price"] for o in orders if not o.get("is_buy_order")]
        if buy_prices:
            best_buy = max(buy_prices)
        if sell_prices:
            best_sell = min(sell_prices)

    return MarketPrice(
        type_id=type_id,
        region_id=region_id,
        best_buy=best_buy,
        best_sell=best_sell,
        cached_at=time.time(),
    )


async def get_average_prices() -> dict[int, float]:
    """Return {type_id: average_price} from ESI /markets/prices/ (global, public).

    This single endpoint covers every published type and is the standard basis
    for killmail valuation. The underlying ESI client caches the HTTP payload
    (stale-while-revalidate), so repeated calls are cheap.
    """
    esi = get_esi_client()
    try:
        data = await esi.get("/markets/prices/")
    except Exception:
        logger.exception("ESI /markets/prices/ fetch failed")
        return {}
    out: dict[int, float] = {}
    if isinstance(data, list):
        for row in data:
            tid = row.get("type_id")
            price = row.get("average_price") or row.get("adjusted_price")
            if tid and price:
                out[tid] = price
    return out


async def get_market_prices(
    type_ids: list[int],
    region_id: int | None = None,
) -> dict[int, MarketPrice]:
    if not type_ids:
        return {}

    if region_id is None:
        region_id = await get_configured_region_id()

    unique_ids = list(set(type_ids))

    cached_results = await asyncio.gather(*[_get_cached_price(region_id, tid) for tid in unique_ids])

    result: dict[int, MarketPrice] = {}
    missing: list[int] = []

    for tid, cached in zip(unique_ids, cached_results):
        if cached is not None:
            result[tid] = cached
        else:
            missing.append(tid)

    if missing:
        fetched = await asyncio.gather(*[_fetch_price_from_esi(region_id, tid) for tid in missing])
        await asyncio.gather(*[_set_cached_price(price) for price in fetched])
        for price in fetched:
            result[price.type_id] = price

    return result
