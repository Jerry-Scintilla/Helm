"""Sync alliance public info (no token required)."""
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.alliance import Alliance, AllianceCorporation
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


async def upsert_alliance(alliance_id: int) -> None:
    esi = get_esi_client()
    try:
        data = await esi.get(f"/alliances/{alliance_id}/")
    except Exception:
        return

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        stmt = (
            insert(Alliance)
            .values(
                alliance_id=alliance_id,
                name=data.get("name", ""),
                ticker=data.get("ticker", ""),
                creator_corp_id=data.get("creator_corporation_id"),
                executor_corp_id=data.get("executor_corporation_id"),
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["alliance_id"],
                set_={
                    "name": data.get("name", ""),
                    "ticker": data.get("ticker", ""),
                    "executor_corp_id": data.get("executor_corporation_id"),
                    "updated_at": now,
                },
            )
            .returning(Alliance.id)
        )
        result = await db.execute(stmt)
        await db.commit()
        row = result.fetchone()

    if row is None:
        return

    alliance_db_id = row[0]

    try:
        corp_ids = await esi.get(f"/alliances/{alliance_id}/corporations/")
    except Exception:
        return

    if not isinstance(corp_ids, list):
        return

    async with AsyncSessionLocal() as db:
        for corp_id in corp_ids:
            stmt = (
                insert(AllianceCorporation)
                .values(alliance_id=alliance_db_id, corporation_id=corp_id)
                .on_conflict_do_nothing(constraint="uq_alliance_corp")
            )
            await db.execute(stmt)
        await db.commit()


@celery_app.task(name="app.tasks.alliances.info.sync_all_alliances")
def sync_all_alliances() -> None:
    async def _run():
        characters = await get_active_characters()
        seen_alliance_ids: set[int] = set()
        for char in characters:
            if char.alliance_id and char.alliance_id not in seen_alliance_ids:
                await upsert_alliance(char.alliance_id)
                seen_alliance_ids.add(char.alliance_id)
    run_async(_run())
