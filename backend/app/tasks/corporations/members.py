"""Sync corporation member tracking (requires director token)."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.corporation import Corporation, CorporationMember
from app.tasks.celery_app import celery_app
from app.tasks.corporations.info import upsert_corporation
from app.tasks.utils import get_director_characters, run_async


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _sync_corporation_members(character: Character) -> None:
    if not character.corporation_id:
        return

    corp = await upsert_corporation(character.corporation_id)
    if corp is None:
        return

    esi = get_esi_client()
    try:
        tracking = await esi.get(
            f"/corporations/{character.corporation_id}/membertracking/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    if not isinstance(tracking, list):
        return

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        for member in tracking:
            stmt = (
                insert(CorporationMember)
                .values(
                    corporation_id=corp.id,
                    character_id=member["character_id"],
                    ship_type_id=member.get("ship_type_id"),
                    start_date=_parse_dt(member.get("start_date")),
                    logon_date=_parse_dt(member.get("logon_date")),
                    logoff_date=_parse_dt(member.get("logoff_date")),
                    location_id=member.get("location_id"),
                    updated_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_corp_member",
                    set_={
                        "ship_type_id": member.get("ship_type_id"),
                        "logon_date": _parse_dt(member.get("logon_date")),
                        "logoff_date": _parse_dt(member.get("logoff_date")),
                        "location_id": member.get("location_id"),
                        "updated_at": now,
                    },
                )
            )
            await db.execute(stmt)
        await db.commit()


@celery_app.task(name="app.tasks.corporations.members.sync_all_corporation_members")
def sync_all_corporation_members() -> None:
    async def _run():
        directors = await get_director_characters()
        seen_corp_ids: set[int] = set()
        for char in directors:
            if char.corporation_id and char.corporation_id not in seen_corp_ids:
                await _sync_corporation_members(char)
                seen_corp_ids.add(char.corporation_id)
    run_async(_run())
