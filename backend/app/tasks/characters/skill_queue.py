from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterSkillQueue
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _update_skill_queue(character: Character) -> None:
    esi = get_esi_client()
    try:
        entries = await esi.get(
            f"/characters/{character.character_id}/skillqueue/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    if entries is None:
        return

    async with AsyncSessionLocal() as db:
        # Full replace — skill queue changes frequently
        await db.execute(delete(CharacterSkillQueue).where(CharacterSkillQueue.character_id == character.id))
        for entry in entries:
            db.add(CharacterSkillQueue(
                character_id=character.id,
                queue_position=entry.get("queue_position", 0),
                skill_id=entry.get("skill_id", 0),
                finished_level=entry.get("finished_level", 0),
                start_date=_parse_dt(entry.get("start_date")),
                finish_date=_parse_dt(entry.get("finish_date")),
                training_start_sp=entry.get("training_start_sp"),
                level_start_sp=entry.get("level_start_sp"),
                level_end_sp=entry.get("level_end_sp"),
            ))
        await db.commit()


@celery_app.task(name="app.tasks.characters.skill_queue.update_skill_queue")
def update_skill_queue(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_skill_queue(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.skill_queue.update_all_skill_queues")
def update_all_skill_queues() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_skill_queue(char)
    run_async(_run())
