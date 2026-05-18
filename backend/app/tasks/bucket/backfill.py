"""One-shot backfill: assign all existing characters that have no bucket token."""
import logging

from sqlalchemy import select

from app.core.bucket import assign_to_bucket
from app.core.database import AsyncSessionLocal
from app.models.bucket import BucketToken
from app.models.character import Character
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)


async def _run_backfill() -> int:
    async with AsyncSessionLocal() as db:
        assigned_ids = select(BucketToken.character_id)
        result = await db.execute(
            select(Character.id).where(Character.id.not_in(assigned_ids))
        )
        unassigned = [row[0] for row in result.fetchall()]

    count = 0
    for char_id in unassigned:
        try:
            async with AsyncSessionLocal() as db:
                await assign_to_bucket(char_id, db)
                await db.commit()
                count += 1
        except Exception as exc:
            logger.error("Backfill failed for character %d: %s", char_id, exc)

    logger.info("Bucket backfill complete: assigned %d characters", count)
    return count


@celery_app.task(name="app.tasks.bucket.backfill.backfill_bucket_assignments")
def backfill_bucket_assignments() -> int:
    return run_async(_run_backfill())
