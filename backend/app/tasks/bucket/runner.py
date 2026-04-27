"""Bucket runner — executes ESI refresh for a batch of characters."""
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.bucket import BucketToken
from app.models.character import Character
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)


async def _refresh_character(char: Character) -> None:
    """Run all ESI refresh tasks for a single character."""
    from app.tasks.characters.wallet import _update_wallet  # noqa: PLC0415
    from app.tasks.characters.skills import _update_skills  # noqa: PLC0415
    from app.tasks.characters.assets import _update_assets  # noqa: PLC0415
    from app.tasks.characters.mail import _update_mail, _fetch_mail_bodies  # noqa: PLC0415
    from app.tasks.characters.wallet_journal import _update_wallet_journal  # noqa: PLC0415
    from app.tasks.characters.wallet_transactions import _update_wallet_transactions  # noqa: PLC0415
    from app.tasks.characters.skill_queue import _update_skill_queue  # noqa: PLC0415
    from app.tasks.characters.notifications import _update_notifications  # noqa: PLC0415

    for fn in [
        _update_wallet, _update_skills, _update_assets,
        _update_mail, _fetch_mail_bodies,
        _update_wallet_journal, _update_wallet_transactions,
        _update_skill_queue, _update_notifications,
    ]:
        try:
            await fn(char)
        except Exception as exc:
            logger.warning("refresh_character(%d) %s failed: %s", char.character_id, fn.__name__, exc)


async def _run_runner(bucket_id: int, character_ids: list[int]) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Character).where(Character.id.in_(character_ids))
        )
        characters = list(result.scalars().all())

    now = datetime.now(UTC)
    for char in characters:
        try:
            await _refresh_character(char)
            # Update BucketToken refresh tracking
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(BucketToken).where(
                        BucketToken.bucket_id == bucket_id,
                        BucketToken.character_id == char.id,
                    )
                )
                token = result.scalar_one_or_none()
                if token:
                    token.last_refreshed_at = now
                    token.refresh_count += 1
                    await db.commit()
        except Exception as exc:
            logger.error("Runner failed for character %d: %s", char.id, exc)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(BucketToken).where(
                        BucketToken.bucket_id == bucket_id,
                        BucketToken.character_id == char.id,
                    )
                )
                token = result.scalar_one_or_none()
                if token:
                    token.error_count += 1
                    await db.commit()


@celery_app.task(name="app.tasks.bucket.runner.refresh_bucket_tokens")
def refresh_bucket_tokens(bucket_id: int, character_ids: list[int]) -> None:
    run_async(_run_runner(bucket_id, character_ids))
