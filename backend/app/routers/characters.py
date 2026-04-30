from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.character import Character
from app.models.esi_data import (
    CharacterAsset, CharacterMail, CharacterSkill, CharacterWallet,
    CharacterWalletJournal, CharacterWalletTransaction, CharacterSkillQueue, CharacterNotification,
)
from app.models.user import User
from app.services.esi_names import enrich_entity_names
from app.services.sde import enrich_type_names, enrich_type_names_all_locales
from app.plugins.registry import extension_registry
from app.plugins.base import CharacterExtensionProvider
import logging

# 强制设置日志级别，确保 INFO 日志可见
_logger = logging.getLogger(__name__)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

logger = _logger

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
            "is_primary": c.is_primary,
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

    # 聚合插件扩展数据
    extensions = []
    _logger.debug("All registered extension points: %s", extension_registry.list_points())
    providers = extension_registry.get_all("character.extension")
    _logger.debug("Found %d providers for character_id=%s", len(providers), char.character_id)
    for provider in providers:
        _logger.debug("Provider: %s, is_protocol: %s", provider, isinstance(provider, CharacterExtensionProvider))
        if isinstance(provider, CharacterExtensionProvider):
            try:
                ext = await provider.get_character_extension(char.character_id, db)
                _logger.debug("Extension result from %s: %s", getattr(provider, '_helm_plugin_name', 'unknown'), ext)
                if ext and ext.character_id == char.character_id:
                    extensions.append({
                        "plugin_name": getattr(provider, "_helm_plugin_name", "unknown"),
                        "title": ext.title,
                        "widget": ext.widget,
                        "content": ext.content,
                        "order": ext.order,
                        "css_class": ext.css_class,
                    })
            except Exception as e:
                logger.warning(f"Plugin extension error in {getattr(provider, '_helm_plugin_name', 'unknown')}: {e}", exc_info=True)

    extensions.sort(key=lambda x: x["order"])

    return {
        "character_id": char.character_id,
        "character_name": char.character_name,
        "corporation_id": char.corporation_id,
        "alliance_id": char.alliance_id,
        "scopes": char.scopes,
        "updated_at": char.updated_at,
        "extensions": extensions,
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
    # Resolve location names for solar_system and station entries via ESI
    resolvable = [r for r in asset_rows if r["location_type"] in ("solar_system", "station")]
    await enrich_entity_names(resolvable, id_field="location_id", name_field="location_name")
    for row in asset_rows:
        row.setdefault("location_name", None)
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
    mail_rows = [
        {
            "mail_id": m.mail_id,
            "subject": m.subject,
            "from_id": m.from_id,
            "timestamp": m.timestamp,
            "is_read": m.is_read,
        }
        for m in mails
    ]
    await enrich_entity_names(mail_rows, id_field="from_id", name_field="from_name")
    return mail_rows


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
    detail_rows = [{"from_id": mail.from_id}]
    await enrich_entity_names(detail_rows, id_field="from_id", name_field="from_name")
    return {
        "mail_id": mail.mail_id,
        "subject": mail.subject,
        "from_id": mail.from_id,
        "from_name": detail_rows[0].get("from_name"),
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
    notif_rows = [
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
    # Skip sender_type="other" (system notifications) — no ESI name available
    await enrich_entity_names(
        notif_rows,
        id_field="sender_id",
        name_field="sender_name",
        skip_types={"other"},
        type_field="sender_type",
    )
    return notif_rows


@router.post("/{character_id}/set-primary")
async def set_primary_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)

    # Clear primary flag on all user's characters, then set on target
    await db.execute(
        update(Character)
        .where(Character.user_id == current_user.id)
        .values(is_primary=False)
    )
    char.is_primary = True
    current_user.username = char.character_name
    await db.commit()

    return {"ok": True, "character_id": char.character_id, "character_name": char.character_name}


@router.delete("/{character_id}")
async def unbind_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)

    if char.is_primary:
        raise HTTPException(status_code=400, detail="不能解绑主角色，请先将其他角色设为主角色")

    # Ensure user has at least one other character
    result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id,
            Character.character_id != character_id,
            Character.is_active == True,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="账号至少需要保留一个角色")

    await db.delete(char)
    await db.commit()
    return Response(status_code=204)
