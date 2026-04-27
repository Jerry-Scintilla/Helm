"""Bucket scheduler — dispatches ESI refresh tasks to buckets every minute."""
import json
import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_pool
from app.models.bucket import Bucket, BucketToken
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)

_BUCKET_STATE_TTL = 90
_BUCKET_CONFIG_CACHE_TTL = 300
_BUCKET_CONFIG_CACHE_KEY = "helm:bucket:config"


def _redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


def _state_key(bucket_id: int) -> str:
    return f"helm:bucket:{bucket_id}:state"


def _health(token_count: int, capacity: int) -> str:
    if capacity == 0:
        return "unknown"
    ratio = token_count / capacity
    if ratio < 0.8:
        return "available"
    if ratio < 0.95:
        return "balanced"
    return "overload"


async def _get_active_buckets() -> list[Bucket]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Bucket).where(Bucket.is_active == True))
        return list(result.scalars().all())


async def _get_due_tokens(bucket_id: int, capacity: int) -> list[int]:
    """Return up to `capacity` character IDs due for refresh in this bucket."""
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.bucket_min_refresh_interval)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BucketToken.character_id).where(
                BucketToken.bucket_id == bucket_id,
                (BucketToken.last_refreshed_at == None) | (BucketToken.last_refreshed_at <= cutoff),
            ).limit(capacity)
        )
        return [row[0] for row in result.fetchall()]


async def _run_scheduler() -> None:
    buckets = await _get_active_buckets()
    if not buckets:
        logger.warning("Bucket scheduler: no active buckets found")
        return

    async with _redis() as r:
        for bucket in buckets:
            due_ids = await _get_due_tokens(bucket.id, bucket.capacity)
            if not due_ids:
                continue

            # Dispatch runner task
            from app.tasks.bucket.runner import refresh_bucket_tokens  # noqa: PLC0415
            refresh_bucket_tokens.apply_async(
                args=[bucket.id, due_ids],
                queue="bucket",
            )

            # Update Redis state
            token_count = len(due_ids)
            state = {
                "last_run_at": datetime.now(UTC).isoformat(),
                "token_count": token_count,
                "active_task_count": 1,
                "health": _health(token_count, bucket.capacity),
            }
            await r.set(_state_key(bucket.id), json.dumps(state), ex=_BUCKET_STATE_TTL)
            logger.info("Bucket %s: dispatched %d tokens", bucket.name, token_count)


@celery_app.task(name="app.tasks.bucket.scheduler.run_bucket_scheduler")
def run_bucket_scheduler() -> None:
    run_async(_run_scheduler())
