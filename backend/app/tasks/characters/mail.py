from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.esi_data import CharacterMail
from app.tasks.celery_app import celery_app
from app.tasks.utils import get_active_characters, run_async


async def _update_mail(character: Character) -> None:
    esi = get_esi_client()
    try:
        mails = await esi.get(
            f"/characters/{character.character_id}/mail/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
    except Exception:
        return

    if not isinstance(mails, list):
        return

    async with AsyncSessionLocal() as db:
        for mail in mails:
            result = await db.execute(
                select(CharacterMail).where(
                    CharacterMail.character_id == character.id,
                    CharacterMail.mail_id == mail["mail_id"],
                )
            )
            row = result.scalar_one_or_none()
            timestamp = None
            if mail.get("timestamp"):
                try:
                    timestamp = datetime.fromisoformat(mail["timestamp"].replace("Z", "+00:00"))
                except ValueError:
                    pass
            if row is None:
                db.add(CharacterMail(
                    character_id=character.id,
                    mail_id=mail["mail_id"],
                    subject=mail.get("subject", ""),
                    from_id=mail.get("from_id"),
                    timestamp=timestamp,
                    is_read=mail.get("is_read", False),
                    body=mail.get("body", ""),
                ))
            else:
                row.is_read = mail.get("is_read", False)
                row.subject = mail.get("subject", row.subject)
                row.from_id = mail.get("from_id", row.from_id)
                row.updated_at = datetime.now(UTC)
        await db.commit()


async def _fetch_mail_body(character: Character, mail_id: int) -> None:
    """Fetch body for a single mail."""
    esi = get_esi_client()
    try:
        data = await esi.get(
            f"/characters/{character.character_id}/mail/{mail_id}/",
            token=character.access_token,
            refresh_token=character.refresh_token,
            character_id=character.character_id,
        )
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(CharacterMail).where(
                    CharacterMail.character_id == character.id,
                    CharacterMail.mail_id == mail_id,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                row.body = data.get("body", "")
                row.updated_at = datetime.now(UTC)
                await db.commit()
    except Exception:
        pass


@celery_app.task(name="app.tasks.characters.mail.update_mail")
def update_mail(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_mail(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.mail.fetch_mail_body")
def fetch_mail_body(character_db_id: int, mail_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _fetch_mail_body(char, mail_id)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.mail.update_all_mail")
def update_all_mail() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_mail(char)
            # fetch all empty bodies for this character
            await _fetch_all_empty_bodies(char)
    run_async(_run())


async def _fetch_all_empty_bodies(character: Character) -> None:
    """Fetch bodies for all mails with empty body for a character."""
    esi = get_esi_client()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CharacterMail).where(
                CharacterMail.character_id == character.id,
                CharacterMail.body == "",
            ).limit(50)
        )
        empty_mails = list(result.scalars().all())

    for mail in empty_mails:
        try:
            data = await esi.get(
                f"/characters/{character.character_id}/mail/{mail.mail_id}/",
                token=character.access_token,
                refresh_token=character.refresh_token,
                character_id=character.character_id,
            )
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CharacterMail).where(CharacterMail.id == mail.id))
                row = result.scalar_one_or_none()
                if row:
                    row.body = data.get("body", "")
                    row.updated_at = datetime.now(UTC)
                    await db.commit()
        except Exception:
            continue
