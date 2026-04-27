"""Sync public corporation info (no token required)."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.corporation import Corporation
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_director_characters, run_async


async def upsert_corporation(corporation_id: int) -> Corporation | None:
    """Fetch and upsert corporation public info, return the DB row."""
    esi = get_esi_client()
    try:
        data = await esi.get(f"/corporations/{corporation_id}/")
    except Exception:
        return None

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        stmt = (
            insert(Corporation)
            .values(
                corporation_id=corporation_id,
                name=data.get("name", ""),
                ticker=data.get("ticker", ""),
                member_count=data.get("member_count", 0),
                ceo_id=data.get("ceo_id"),
                alliance_id=data.get("alliance_id"),
                description=data.get("description", ""),
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["corporation_id"],
                set_={
                    "name": data.get("name", ""),
                    "ticker": data.get("ticker", ""),
                    "member_count": data.get("member_count", 0),
                    "ceo_id": data.get("ceo_id"),
                    "alliance_id": data.get("alliance_id"),
                    "description": data.get("description", ""),
                    "updated_at": now,
                },
            )
            .returning(Corporation.id)
        )
        result = await db.execute(stmt)
        await db.commit()
        corp_id_row = result.fetchone()

    if corp_id_row is None:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Corporation).where(Corporation.corporation_id == corporation_id))
        return result.scalar_one_or_none()


@celery_app.task(name="app.tasks.corporations.info.sync_all_corporations")
def sync_all_corporations() -> None:
    async def _run():
        directors = await get_director_characters()
        seen_corp_ids: set[int] = set()
        for char in directors:
            if char.corporation_id and char.corporation_id not in seen_corp_ids:
                await upsert_corporation(char.corporation_id)
                seen_corp_ids.add(char.corporation_id)
    run_async(_run())
