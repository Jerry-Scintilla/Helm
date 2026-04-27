from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterWalletTransaction
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _update_wallet_transactions(character: Character) -> None:
    esi = get_esi_client()
    try:
        entries = await esi.get(
            f"/characters/{character.character_id}/wallet/transactions/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
            paginate=True,
        )
    except Exception:
        return

    if not entries:
        return

    async with AsyncSessionLocal() as db:
        for entry in entries:
            stmt = (
                insert(CharacterWalletTransaction)
                .values(
                    character_id=character.id,
                    transaction_id=entry["transaction_id"],
                    date=_parse_dt(entry.get("date")),
                    type_id=entry.get("type_id", 0),
                    location_id=entry.get("location_id", 0),
                    unit_price=entry.get("unit_price", 0.0),
                    quantity=entry.get("quantity", 1),
                    client_id=entry.get("client_id"),
                    is_buy=entry.get("is_buy", False),
                    is_personal=entry.get("is_personal", True),
                    journal_ref_id=entry.get("journal_ref_id"),
                )
                .on_conflict_do_nothing(constraint="uq_char_wallet_tx")
            )
            await db.execute(stmt)
        await db.commit()


@celery_app.task(name="app.tasks.characters.wallet_transactions.update_wallet_transactions")
def update_wallet_transactions(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_wallet_transactions(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.wallet_transactions.update_all_wallet_transactions")
def update_all_wallet_transactions() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_wallet_transactions(char)
    run_async(_run())
