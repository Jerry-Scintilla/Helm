"""Sync recent killmails (last 90 days) from ESI into character_killmails.

The recent list (ids + hashes) requires the esi-killmails scope; the full
killmail used for the summary is fetched from the public, immutable endpoint.
Only killmails not already stored are fetched, capped per run to bound load.
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.cache import delete_prefix
from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterKillmail
from app.services.killmails import build_summary
from app.services.market import get_average_prices
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async

_SCOPE = "esi-killmails.read_killmails.v1"
_MAX_NEW_PER_RUN = 50


async def _update_killmails(character: Character) -> None:
    scopes = set((character.scopes or "").split())
    if _SCOPE not in scopes:
        return

    esi = get_esi_client()
    try:
        recent = await esi.get(
            f"/characters/{character.character_id}/killmails/recent/",
            token=character.access_token, refresh_token=character.refresh_token,
            character_id=character.character_id, paginate=True,
        )
    except Exception:
        return
    if not isinstance(recent, list) or not recent:
        return

    # Skip killmails already stored.
    async with AsyncSessionLocal() as db:
        existing = set((await db.execute(
            select(CharacterKillmail.killmail_id).where(
                CharacterKillmail.character_id == character.id
            )
        )).scalars().all())

    new_entries = [r for r in recent if r.get("killmail_id") not in existing][:_MAX_NEW_PER_RUN]
    if not new_entries:
        return

    prices = await get_average_prices()
    now = datetime.now(UTC)

    rows: list[dict] = []
    for entry in new_entries:
        km_id = entry.get("killmail_id")
        km_hash = entry.get("killmail_hash")
        if not km_id or not km_hash:
            continue
        try:
            km = await esi.get(f"/killmails/{km_id}/{km_hash}/")
        except Exception:
            continue
        if not isinstance(km, dict):
            continue
        summary = await build_summary(km, character.character_id, prices)
        rows.append({
            "character_id": character.id,
            "killmail_id": km_id,
            "killmail_hash": km_hash,
            "updated_at": now,
            **summary,
        })

    if not rows:
        return

    # Single batched insert + commit instead of one round-trip per killmail.
    async with AsyncSessionLocal() as db:
        await db.execute(
            insert(CharacterKillmail)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_char_killmail")
        )
        await db.commit()

    # Rebuild the derived list-response cache from the freshly-synced rows.
    await delete_prefix(f"killmails:list:{character.id}:")


@celery_app.task(name="app.tasks.characters.killmails.update_killmails")
def update_killmails(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_killmails(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.killmails.update_all_killmails")
def update_all_killmails() -> None:
    async def _run():
        for char in await get_active_characters():
            await _update_killmails(char)
    run_async(_run())
