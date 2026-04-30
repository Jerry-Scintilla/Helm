"""Sync character public info (corporation_id, alliance_id) from ESI."""
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


REFRESH_TTL = 600  # 10 minutes


async def _update_character_info(character: Character) -> None:
    """Fetch and update corporation_id and alliance_id from ESI."""
    esi = get_esi_client()
    now = datetime.now(UTC)

    try:
        data = await esi.get(
            f"/characters/{character.character_id}/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    if data is None:
        return

    corporation_id = data.get("corporation_id")
    alliance_id = data.get("alliance_id")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Character).where(Character.id == character.id))
        char = result.scalar_one_or_none()
        if char is None:
            return

        if corporation_id is not None:
            char.corporation_id = corporation_id
            char.corporation_updated_at = now
        if alliance_id is not None:
            char.alliance_id = alliance_id
            char.alliance_updated_at = now

        await db.commit()


@celery_app.task(name="app.tasks.characters.info.update_character_info")
def update_character_info(character_db_id: int) -> None:
    """Update corporation/alliance info for a single character."""
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_character_info(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.info.update_all_character_info")
def update_all_character_info() -> None:
    """Update corporation/alliance info for all active characters."""
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_character_info(char)
    run_async(_run())
