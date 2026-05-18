"""Shared ESI token persistence callback — used by both FastAPI and Celery worker."""
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def persist_refreshed_token(eve_character_id: int, access_token: str, refresh_token: str) -> None:
    """Write a freshly refreshed ESI token pair back to the characters table."""
    from app.models.character import Character
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Character).where(Character.character_id == eve_character_id))
        char = result.scalar_one_or_none()
        if char:
            char.access_token = access_token
            char.refresh_token = refresh_token
            await db.commit()
            logger.debug("Persisted refreshed token for character %d", eve_character_id)
