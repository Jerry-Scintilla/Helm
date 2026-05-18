"""Bucket auto-assignment: place every character into a bucket automatically."""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bucket import Bucket, BucketToken

logger = logging.getLogger(__name__)

_DEFAULT_CAPACITY = 100


async def assign_to_bucket(character_db_id: int, db: AsyncSession) -> None:
    """Assign character to the first bucket with available space.

    Creates a new auto-named bucket when all existing buckets are at capacity.
    Safe to call on already-assigned characters (no-op).
    """
    existing = (await db.execute(
        select(BucketToken).where(BucketToken.character_id == character_db_id)
    )).scalar_one_or_none()
    if existing is not None:
        return

    # Count tokens per bucket in a subquery so we can compare against capacity
    token_counts = (
        select(BucketToken.bucket_id, func.count().label("cnt"))
        .group_by(BucketToken.bucket_id)
        .subquery()
    )
    result = await db.execute(
        select(Bucket)
        .outerjoin(token_counts, Bucket.id == token_counts.c.bucket_id)
        .where(
            Bucket.is_active == True,
            (token_counts.c.cnt == None) | (token_counts.c.cnt < Bucket.capacity),
        )
        # Fill existing buckets before creating new ones
        .order_by(func.coalesce(token_counts.c.cnt, 0).desc())
        .limit(1)
    )
    bucket = result.scalar_one_or_none()

    if bucket is None:
        total = (await db.execute(select(func.count()).select_from(Bucket))).scalar() or 0
        bucket = Bucket(name=f"auto-{total + 1}", capacity=_DEFAULT_CAPACITY)
        db.add(bucket)
        await db.flush()
        logger.info("Created new bucket: %s", bucket.name)

    db.add(BucketToken(bucket_id=bucket.id, character_id=character_db_id))
    logger.info("Assigned character %d to bucket %s (id=%d)", character_db_id, bucket.name, bucket.id)
