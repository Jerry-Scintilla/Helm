from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.character import Character
from app.models.esi_data import (
    CharacterAsset, CharacterMail, CharacterSkill, CharacterWallet,
    CharacterWalletJournal, CharacterWalletTransaction, CharacterSkillQueue, CharacterNotification,
)
from app.models.user import User
from app.services.sde import enrich_type_names, enrich_type_names_all_locales

router = APIRouter(prefix="/api/v1/characters", tags=["characters"])


async def _get_character_for_user(
    character_id: int, user: User, db: AsyncSession
) -> Character:
    result = await db.execute(
        select(Character).where(
            Character.character_id == character_id,
            Character.user_id == user.id,
        )
    )
    char = result.scalar_one_or_none()
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return char


@router.get("/")
async def list_characters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    result = await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_active == True)
    )
    characters = result.scalars().all()
    return [
        {
            "character_id": c.character_id,
            "character_name": c.character_name,
            "corporation_id": c.corporation_id,
            "alliance_id": c.alliance_id,
        }
        for c in characters
    ]


@router.get("/{character_id}/")
async def get_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    return {
        "character_id": char.character_id,
        "character_name": char.character_name,
        "corporation_id": char.corporation_id,
        "alliance_id": char.alliance_id,
        "scopes": char.scopes,
        "updated_at": char.updated_at,
    }


@router.get("/{character_id}/wallet")
async def get_wallet(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterWallet).where(CharacterWallet.character_id == char.id)
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        return {"balance": None, "updated_at": None}
    return {"balance": wallet.balance, "updated_at": wallet.updated_at}


@router.get("/{character_id}/skills")
async def get_skills(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterSkill).where(CharacterSkill.character_id == char.id)
    )
    skills = result.scalars().all()
    skill_rows = [
        {
            "skill_id": s.skill_id,
            "trained_skill_level": s.trained_skill_level,
            "skillpoints_in_skill": s.skillpoints_in_skill,
        }
        for s in skills
    ]
    await enrich_type_names_all_locales(skill_rows, id_field="skill_id", name_field="skill_name", db=db)
    return {
        "total_sp": sum(s.skillpoints_in_skill for s in skills),
        "skills": skill_rows,
        "updated_at": skills[0].updated_at if skills else None,
    }


@router.get("/{character_id}/assets")
async def get_assets(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterAsset).where(CharacterAsset.character_id == char.id)
    )
    assets = result.scalars().all()
    asset_rows = [
        {
            "item_id": a.item_id,
            "type_id": a.type_id,
            "location_id": a.location_id,
            "location_type": a.location_type,
            "quantity": a.quantity,
        }
        for a in assets
    ]
    await enrich_type_names_all_locales(asset_rows, id_field="type_id", name_field="type_name", db=db)
    return asset_rows


@router.get("/{character_id}/mail")
async def get_mail(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterMail)
        .where(CharacterMail.character_id == char.id)
        .order_by(CharacterMail.timestamp.desc())
        .limit(50)
    )
    mails = result.scalars().all()
    return [
        {
            "mail_id": m.mail_id,
            "subject": m.subject,
            "from_id": m.from_id,
            "timestamp": m.timestamp,
            "is_read": m.is_read,
        }
        for m in mails
    ]


@router.get("/{character_id}/mail/{mail_id}")
async def get_mail_detail(
    character_id: int,
    mail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterMail).where(
            CharacterMail.character_id == char.id,
            CharacterMail.mail_id == mail_id,
        )
    )
    mail = result.scalar_one_or_none()
    if mail is None:
        raise HTTPException(status_code=404, detail="Mail not found")
    return {
        "mail_id": mail.mail_id,
        "subject": mail.subject,
        "from_id": mail.from_id,
        "timestamp": mail.timestamp,
        "is_read": mail.is_read,
        "body": mail.body,
    }


@router.get("/{character_id}/wallet/journal")
async def get_wallet_journal(
    character_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterWalletJournal)
        .where(CharacterWalletJournal.character_id == char.id)
        .order_by(CharacterWalletJournal.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "journal_id": e.journal_id,
            "date": e.date,
            "ref_type": e.ref_type,
            "first_party_id": e.first_party_id,
            "second_party_id": e.second_party_id,
            "amount": e.amount,
            "balance": e.balance,
            "description": e.description,
        }
        for e in entries
    ]


@router.get("/{character_id}/wallet/transactions")
async def get_wallet_transactions(
    character_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterWalletTransaction)
        .where(CharacterWalletTransaction.character_id == char.id)
        .order_by(CharacterWalletTransaction.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()
    tx_rows = [
        {
            "transaction_id": e.transaction_id,
            "date": e.date,
            "type_id": e.type_id,
            "location_id": e.location_id,
            "unit_price": e.unit_price,
            "quantity": e.quantity,
            "client_id": e.client_id,
            "is_buy": e.is_buy,
        }
        for e in entries
    ]
    await enrich_type_names_all_locales(tx_rows, id_field="type_id", name_field="type_name", db=db)
    return tx_rows


@router.get("/{character_id}/skillqueue")
async def get_skill_queue(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterSkillQueue)
        .where(CharacterSkillQueue.character_id == char.id)
        .order_by(CharacterSkillQueue.queue_position)
    )
    queue = result.scalars().all()
    queue_rows = [
        {
            "queue_position": q.queue_position,
            "skill_id": q.skill_id,
            "finished_level": q.finished_level,
            "start_date": q.start_date,
            "finish_date": q.finish_date,
            "level_start_sp": q.level_start_sp,
            "level_end_sp": q.level_end_sp,
        }
        for q in queue
    ]
    await enrich_type_names_all_locales(queue_rows, id_field="skill_id", name_field="skill_name", db=db)
    return queue_rows


@router.get("/{character_id}/notifications")
async def get_notifications(
    character_id: int,
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    stmt = (
        select(CharacterNotification)
        .where(CharacterNotification.character_id == char.id)
        .order_by(CharacterNotification.timestamp.desc())
        .limit(50)
    )
    if unread_only:
        stmt = stmt.where(CharacterNotification.is_read == False)
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    return [
        {
            "notification_id": n.notification_id,
            "type": n.type,
            "sender_id": n.sender_id,
            "sender_type": n.sender_type,
            "timestamp": n.timestamp,
            "is_read": n.is_read,
            "text": n.text,
        }
        for n in notifications
    ]
