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
                    from_id=mail.get("from"),
                    timestamp=timestamp,
                    is_read=mail.get("is_read", False),
                ))
            else:
                row.is_read = mail.get("is_read", False)
                row.updated_at = datetime.now(UTC)
        await db.commit()


@celery_app.task(name="app.tasks.characters.mail.update_mail")
def update_mail(character_db_id: int) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Character).where(Character.id == character_db_id))
            char = result.scalar_one_or_none()
        if char:
            await _update_mail(char)
    run_async(_run())


@celery_app.task(name="app.tasks.characters.mail.update_all_mail")
def update_all_mail() -> None:
    async def _run():
        characters = await get_active_characters()
        for char in characters:
            await _update_mail(char)
    run_async(_run())
