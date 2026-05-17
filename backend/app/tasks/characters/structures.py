"""Resolve player-owned Upwell structure names via ESI and cache in DB."""
import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import PlayerStructure
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)

# ESI allows ~3 req/s safely; 0.4s between calls keeps us well under the limit
_ESI_DELAY = 0.4


async def _resolve_structures(structure_ids: list[int], character_db_id: int) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Character).where(Character.id == character_db_id))
        char = result.scalar_one_or_none()
    if char is None:
        return

    esi = get_esi_client()
    now = datetime.now(UTC)

    for sid in structure_ids:
        name: str | None = None
        try:
            data = await esi.get(
                f"/universe/structures/{sid}/",
                token=char.access_token,
                refresh_token=char.refresh_token,
                character_id=char.character_id,
            )
            if isinstance(data, dict):
                name = data.get("name")
        except Exception as exc:
            logger.warning("Failed to resolve structure %d: %s", sid, exc)

        async with AsyncSessionLocal() as db:
            await db.execute(
                insert(PlayerStructure)
                .values(structure_id=sid, name=name, resolved_at=now)
                .on_conflict_do_update(
                    index_elements=["structure_id"],
                    set_={"name": name, "resolved_at": now},
                )
            )
            await db.commit()

        await asyncio.sleep(_ESI_DELAY)


@celery_app.task(name="app.tasks.characters.structures.resolve_player_structures")
def resolve_player_structures(structure_ids: list[int], character_db_id: int) -> None:
    run_async(_resolve_structures(structure_ids, character_db_id))
