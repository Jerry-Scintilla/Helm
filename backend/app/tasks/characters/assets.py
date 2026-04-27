from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterAsset
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


async def _update_assets(character: Character) -> None:
    esi = get_esi_client()
    try:
        assets = await esi.get(
            f"/characters/{character.character_id}/assets/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
            paginate=True,
        )
    except Exception:
        return

    if not isinstance(assets, list):
        return

    async with AsyncSessionLocal() as db:
        # Replace all assets for this character
        await db.execute(delete(CharacterAsset).where(CharacterAsset.character_id == character.id))
        for asset in assets:
            db.add(CharacterAsset(
                character_id=character.id,
                item_id=asset["item_id"],
                type_id=asset["type_id"],
                location_id=asset["location_id"],
                location_type=asset.get("location_type", ""),
                quantity=asset.get("quantity", 1),
                is_singleton=asset.get("is_singleton", False),
            ))
        await db.commit()


@celery_app.task(name="app.tasks.characters.assets.update_assets")
def update_assets(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_assets(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.assets.update_all_assets")
def update_all_assets() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_assets(char)
    run_async(_run())
