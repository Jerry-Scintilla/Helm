"""Sync corporation wallets and wallet journal."""
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.corporation import CorporationWallet, CorporationWalletJournal
from app.tasks.celery_app import celery_app
from app.tasks.corporations.info import upsert_corporation
from app.tasks.utils import get_director_characters, run_async


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _sync_corporation_wallet(character: Character) -> None:
    if not character.corporation_id:
        return

    corp = await upsert_corporation(character.corporation_id)
    if corp is None:
        return

    esi = get_esi_client()
    try:
        wallets = await esi.get(
            f"/corporations/{character.corporation_id}/wallets/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    if not isinstance(wallets, list):
        return

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        for wallet in wallets:
            division = wallet.get("division", 1)
            stmt = (
                insert(CorporationWallet)
                .values(
                    corporation_id=corp.id,
                    wallet_division=division,
                    balance=wallet.get("balance", 0.0),
                    updated_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_corp_wallet_div",
                    set_={"balance": wallet.get("balance", 0.0), "updated_at": now},
                )
            )
            await db.execute(stmt)

            # Fetch journal for this division
            try:
                journal = await esi.get(
                    f"/corporations/{character.corporation_id}/wallets/{division}/journal/",
                    token=character.access_token,
                    refresh_token=character.refresh_token,
                    character_id=character.character_id,
                    paginate=True,
                )
            except Exception:
                continue

            if isinstance(journal, list):
                for entry in journal:
                    jstmt = (
                        insert(CorporationWalletJournal)
                        .values(
                            corporation_id=corp.id,
                            division=division,
                            journal_id=entry["id"],
                            date=_parse_dt(entry.get("date")),
                            ref_type=entry.get("ref_type", ""),
                            first_party_id=entry.get("first_party_id"),
                            second_party_id=entry.get("second_party_id"),
                            amount=entry.get("amount"),
                            balance=entry.get("balance"),
                            description=entry.get("description", ""),
                        )
                        .on_conflict_do_nothing(constraint="uq_corp_wallet_journal")
                    )
                    await db.execute(jstmt)

        await db.commit()


@celery_app.task(name="app.tasks.corporations.wallet.sync_all_corporation_wallets")
def sync_all_corporation_wallets() -> None:
    async def _run():
        directors = await get_director_characters()
        seen_corp_ids: set[int] = set()
        for char in directors:
            if char.corporation_id and char.corporation_id not in seen_corp_ids:
                await _sync_corporation_wallet(char)
                seen_corp_ids.add(char.corporation_id)
    run_async(_run())
