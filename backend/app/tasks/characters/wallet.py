from datetime import UTC, datetime

from sqlalchemy import select

from app.cache import logical_delete
from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterWallet
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


async def _update_wallet(character: Character) -> None:
    esi = get_esi_client()
    try:
        balance = await esi.get(
            f"/characters/{character.character_id}/wallet/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CharacterWallet).where(CharacterWallet.character_id == character.id)
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            wallet = CharacterWallet(character_id=character.id, balance=balance)
            db.add(wallet)
        else:
            wallet.balance = balance
            wallet.updated_at = datetime.now(UTC)
        await db.commit()
    await logical_delete(f"wallet:balance:{character.id}")


@celery_app.task(name="app.tasks.characters.wallet.update_wallet")
def update_wallet(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_wallet(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.wallet.update_all_wallets")
def update_all_wallets() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_wallet(char)
    run_async(_run())
