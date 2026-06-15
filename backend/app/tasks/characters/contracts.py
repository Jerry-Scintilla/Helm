"""Sync character + corporation contracts from ESI into character_contracts."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.cache import delete_prefix
from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterContract
from app.services.contracts import parse_dt
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async

_CHAR_SCOPE = "esi-contracts.read_character_contracts.v1"
_CORP_SCOPE = "esi-contracts.read_corporation_contracts.v1"


def _row_values(character_db_id: int, c: dict, source: str) -> dict:
    return {
        "character_id": character_db_id,
        "contract_id": c["contract_id"],
        "source": source,
        "type": c.get("type", "unknown"),
        "status": c.get("status", ""),
        "issuer_id": c.get("issuer_id"),
        "issuer_corporation_id": c.get("issuer_corporation_id"),
        "assignee_id": c.get("assignee_id"),
        "acceptor_id": c.get("acceptor_id"),
        "start_location_id": c.get("start_location_id"),
        "end_location_id": c.get("end_location_id"),
        "for_corporation": c.get("for_corporation", False),
        "availability": c.get("availability"),
        "title": c.get("title") or "",
        "price": c.get("price"),
        "reward": c.get("reward"),
        "collateral": c.get("collateral"),
        "buyout": c.get("buyout"),
        "volume": c.get("volume"),
        "days_to_complete": c.get("days_to_complete"),
        "date_issued": parse_dt(c.get("date_issued")),
        "date_expired": parse_dt(c.get("date_expired")),
        "date_accepted": parse_dt(c.get("date_accepted")),
        "date_completed": parse_dt(c.get("date_completed")),
        "updated_at": datetime.now(UTC),
    }


async def _upsert(character_db_id: int, contracts: list[dict], source: str) -> None:
    if not contracts:
        return
    async with AsyncSessionLocal() as db:
        for c in contracts:
            if not c.get("contract_id"):
                continue
            values = _row_values(character_db_id, c, source)
            update_cols = {k: v for k, v in values.items() if k not in ("character_id", "contract_id")}
            await db.execute(
                insert(CharacterContract)
                .values(**values)
                .on_conflict_do_update(
                    constraint="uq_char_contract",
                    set_=update_cols,
                )
            )
        await db.commit()


async def _update_contracts(character: Character) -> None:
    esi = get_esi_client()
    scopes = set((character.scopes or "").split())

    if _CHAR_SCOPE in scopes:
        try:
            data = await esi.get(
                f"/characters/{character.character_id}/contracts/",
                token=character.access_token, refresh_token=character.refresh_token,
                character_id=character.character_id, paginate=True,
            )
            if isinstance(data, list):
                await _upsert(character.id, data, "character")
        except Exception:
            pass

    if character.corporation_id and _CORP_SCOPE in scopes:
        try:
            data = await esi.get(
                f"/corporations/{character.corporation_id}/contracts/",
                token=character.access_token, refresh_token=character.refresh_token,
                character_id=character.character_id, paginate=True,
            )
            if isinstance(data, list):
                await _upsert(character.id, data, "corporation")
        except Exception:
            pass

    # Invalidate the derived list-response cache so the next read rebuilds it
    # from the freshly-synced rows (the cache is keyed off DB id, all pages).
    await delete_prefix(f"contracts:list:{character.id}:")


@celery_app.task(name="app.tasks.characters.contracts.update_contracts")
def update_contracts(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_contracts(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.contracts.update_all_contracts")
def update_all_contracts() -> None:
    async def _run():
        for char in await get_active_characters():
            await _update_contracts(char)
    run_async(_run())
