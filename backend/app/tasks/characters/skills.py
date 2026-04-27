from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterSkill
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


async def _update_skills(character: Character) -> None:
    esi = get_esi_client()
    try:
        data = await esi.get(
            f"/characters/{character.character_id}/skills/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    skills = data.get("skills", [])
    async with AsyncSessionLocal() as db:
        for skill in skills:
            result = await db.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id == skill["skill_id"],
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                db.add(CharacterSkill(
                    character_id=character.id,
                    skill_id=skill["skill_id"],
                    trained_skill_level=skill.get("trained_skill_level", 0),
                    skillpoints_in_skill=skill.get("skillpoints_in_skill", 0),
                ))
            else:
                row.trained_skill_level = skill.get("trained_skill_level", 0)
                row.skillpoints_in_skill = skill.get("skillpoints_in_skill", 0)
                row.updated_at = datetime.now(UTC)
        await db.commit()


@celery_app.task(name="app.tasks.characters.skills.update_skills")
def update_skills(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_skills(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.skills.update_all_skills")
def update_all_skills() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_skills(char)
    run_async(_run())
