"""Sync corporation assets."""
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.corporation import Corporation, CorporationAsset
from app.tasks.celery_app import celery_app
from app.tasks.corporations.info import upsert_corporation
from app.tasks.utils import get_director_characters, run_async


async def _sync_corporation_assets(character: Character) -> None:
    if not character.corporation_id:
        return

    corp = await upsert_corporation(character.corporation_id)
    if corp is None:
        return

    esi = get_esi_client()
    try:
        assets = await esi.get(
            f"/corporations/{character.corporation_id}/assets/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
            paginate=True,
        )
    except Exception:
        return

    if not isinstance(assets, list):
        return

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        # Full replace per corporation
        await db.execute(delete(CorporationAsset).where(CorporationAsset.corporation_id == corp.id))
        for asset in assets:
            db.add(CorporationAsset(
                corporation_id=corp.id,
                item_id=asset["item_id"],
                type_id=asset.get("type_id", 0),
                location_id=asset.get("location_id", 0),
                location_type=asset.get("location_type", ""),
                quantity=asset.get("quantity", 1),
                is_singleton=asset.get("is_singleton", False),
                updated_at=now,
            ))
        await db.commit()


@celery_app.task(name="app.tasks.corporations.assets.sync_all_corporation_assets")
def sync_all_corporation_assets() -> None:
    async def _run():
        directors = await get_director_characters()
        seen_corp_ids: set[int] = set()
        for char in directors:
            if char.corporation_id and char.corporation_id not in seen_corp_ids:
                await _sync_corporation_assets(char)
                seen_corp_ids.add(char.corporation_id)
    run_async(_run())
