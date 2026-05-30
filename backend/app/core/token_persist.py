"""Shared ESI token persistence callback — used by both FastAPI and Celery worker."""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def persist_refreshed_token(
    eve_character_id: int,
    access_token: str,
    refresh_token: str,
    expires_in: int | None = None,
) -> None:
    """Write a freshly refreshed ESI token pair back to the characters table."""
    from app.models.character import Character
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Character).where(Character.character_id == eve_character_id))
        char = result.scalar_one_or_none()
        if char:
            char.access_token = access_token
            char.refresh_token = refresh_token
            if expires_in:
                char.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
            await db.commit()
            logger.debug("Persisted refreshed token for character %d", eve_character_id)
