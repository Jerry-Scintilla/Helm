from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterNotification
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _update_notifications(character: Character) -> None:
    esi = get_esi_client()
    try:
        entries = await esi.get(
            f"/characters/{character.character_id}/notifications/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    if not entries:
        return

    async with AsyncSessionLocal() as db:
        for entry in entries:
            stmt = (
                insert(CharacterNotification)
                .values(
                    character_id=character.id,
                    notification_id=entry["notification_id"],
                    type=entry.get("type", ""),
                    sender_id=entry.get("sender_id"),
                    sender_type=entry.get("sender_type"),
                    timestamp=_parse_dt(entry.get("timestamp")),
                    is_read=entry.get("is_read", False),
                    text=entry.get("text", ""),
                )
                .on_conflict_do_update(
                    constraint="uq_char_notification",
                    set_={"is_read": entry.get("is_read", False), "text": entry.get("text", "")},
                )
            )
            await db.execute(stmt)
        await db.commit()


@celery_app.task(name="app.tasks.characters.notifications.update_notifications")
def update_notifications(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_notifications(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.notifications.update_all_notifications")
def update_all_notifications() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_notifications(char)
    run_async(_run())
