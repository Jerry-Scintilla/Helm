from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterWalletJournal
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _update_wallet_journal(character: Character) -> None:
    esi = get_esi_client()
    try:
        entries = await esi.get(
            f"/characters/{character.character_id}/wallet/journal/",
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
                insert(CharacterWalletJournal)
                .values(
                    character_id=character.id,
                    journal_id=entry["id"],
                    date=_parse_dt(entry.get("date")),
                    ref_type=entry.get("ref_type", ""),
                    first_party_id=entry.get("first_party_id"),
                    second_party_id=entry.get("second_party_id"),
                    amount=entry.get("amount"),
                    balance=entry.get("balance"),
                    description=entry.get("description", ""),
                    context_id=entry.get("context_id"),
                    context_id_type=entry.get("context_id_type"),
                )
                .on_conflict_do_nothing(constraint="uq_char_wallet_journal")
            )
            await db.execute(stmt)
        await db.commit()


@celery_app.task(name="app.tasks.characters.wallet_journal.update_wallet_journal")
def update_wallet_journal(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_wallet_journal(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.wallet_journal.update_all_wallet_journals")
def update_all_wallet_journals() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_wallet_journal(char)
    run_async(_run())
