import asyncio
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.character import Character
from app.models.esi_data import (
    CharacterAsset, CharacterMail, CharacterSkill, CharacterWallet,
    CharacterWalletJournal, CharacterWalletTransaction, CharacterSkillQueue, CharacterNotification,
    PlayerStructure,
)
from app.models.user import User
from app.services.esi_names import enrich_entity_names, resolve_entity_names
from app.services.sde import enrich_type_names, enrich_type_names_all_locales
from app.plugins.registry import extension_registry
from app.plugins.base import CharacterExtensionProvider
from app.tasks.celery_app import celery_app
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


REFRESH_TTL = 600  # 10 minutes


@router.get("/")
async def list_characters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    result = await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_active == True)
    )
    characters = result.scalars().all()
    now = datetime.now(UTC)

    for c in characters:
        corp_stale = (
            c.corporation_updated_at is None
            or (now - c.corporation_updated_at).total_seconds() > REFRESH_TTL
        )
        ally_stale = (
            c.alliance_updated_at is None
            or (now - c.alliance_updated_at).total_seconds() > REFRESH_TTL
        )
        if corp_stale or ally_stale:
            asyncio.create_task(asyncio.to_thread(
                celery_app.send_task,
                'app.tasks.characters.info.update_character_info',
                args=[c.id],
                queue='characters',
            ))

    # Resolve corporation and alliance names via ESI
    corp_and_alliance_ids = [
        c.corporation_id for c in characters if c.corporation_id
    ] + [
        c.alliance_id for c in characters if c.alliance_id
    ]
    name_map = await resolve_entity_names(corp_and_alliance_ids) if corp_and_alliance_ids else {}

    return [
        {
            "character_id": c.character_id,
            "character_name": c.character_name,
            "corporation_id": c.corporation_id,
            "corporation_name": name_map.get(c.corporation_id, {}).get("name") if c.corporation_id else None,
            "alliance_id": c.alliance_id,
            "alliance_name": name_map.get(c.alliance_id, {}).get("name") if c.alliance_id else None,
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

    corp_and_alliance_ids = [i for i in [char.corporation_id, char.alliance_id] if i]
    name_map = await resolve_entity_names(corp_and_alliance_ids) if corp_and_alliance_ids else {}

    return {
        "character_id": char.character_id,
        "character_name": char.character_name,
        "corporation_id": char.corporation_id,
        "corporation_name": name_map.get(char.corporation_id, {}).get("name") if char.corporation_id else None,
        "alliance_id": char.alliance_id,
        "alliance_name": name_map.get(char.alliance_id, {}).get("name") if char.alliance_id else None,
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
    from app.models.sde import SDEType, SDEGroup
    char = await _get_character_for_user(character_id, current_user, db)

    rows = (await db.execute(
        select(
            CharacterSkill.skill_id,
            CharacterSkill.trained_skill_level,
            CharacterSkill.skillpoints_in_skill,
            CharacterSkill.updated_at,
            SDEType.name.label("skill_name"),
            SDEType.group_id,
            SDEGroup.name.label("group_name"),
        )
        .join(SDEType, SDEType.type_id == CharacterSkill.skill_id, isouter=True)
        .join(SDEGroup, SDEGroup.group_id == SDEType.group_id, isouter=True)
        .where(CharacterSkill.character_id == char.id)
        .order_by(SDEGroup.name["en"].as_string(), SDEType.name["en"].as_string())
    )).all()

    total_sp = sum(r.skillpoints_in_skill for r in rows)
    updated_at = rows[0].updated_at if rows else None

    # 按 group_id 分组
    groups: dict[int, dict] = {}
    for r in rows:
        gid = r.group_id or 0
        if gid not in groups:
            groups[gid] = {
                "group_id": gid,
                "group_name": r.group_name,
                "skills": [],
            }
        groups[gid]["skills"].append({
            "skill_id": r.skill_id,
            "skill_name": r.skill_name,
            "trained_skill_level": r.trained_skill_level,
            "skillpoints_in_skill": r.skillpoints_in_skill,
        })

    return {
        "total_sp": total_sp,
        "groups": list(groups.values()),
        "updated_at": updated_at,
    }


@router.get("/{character_id}/assets")
async def get_assets(
    character_id: int,
    q: str | None = Query(None, description="按地点名称搜索（模糊匹配）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
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
            "is_singleton": a.is_singleton,
        }
        for a in assets
    ]

    await enrich_type_names_all_locales(asset_rows, id_field="type_id", name_field="type_name", db=db)

    # Build lookup: item_id -> row
    by_item_id = {row["item_id"]: row for row in asset_rows}

    # Build children map: parent_item_id -> [child rows]
    children_map: dict[int, list] = defaultdict(list)
    for row in asset_rows:
        if row["location_type"] == "item":
            children_map[row["location_id"]].append(row)

    def build_node(row: dict) -> dict:
        return {
            "item_id": row["item_id"],
            "type_id": row["type_id"],
            "type_name": row.get("type_name"),
            "quantity": row["quantity"],
            "is_singleton": row["is_singleton"],
            "items": [build_node(c) for c in children_map.get(row["item_id"], [])],
        }

    # Group root items (directly in station/solar_system/other) by location_id
    location_groups: dict[int, dict] = {}
    for row in asset_rows:
        if row["location_type"] in ("station", "solar_system", "other"):
            loc_id = row["location_id"]
            if loc_id not in location_groups:
                location_groups[loc_id] = {"location_type": row["location_type"], "items": []}
            location_groups[loc_id]["items"].append(build_node(row))

    # Orphaned: location_type=="item" but parent not in this character's assets.
    # Typically items in corp-owned Upwell structures (the structure is a corp asset,
    # absent from the character's personal asset list).
    orphaned_by_parent: dict[int, list] = defaultdict(list)
    for row in asset_rows:
        if row["location_type"] == "item" and row["location_id"] not in by_item_id:
            orphaned_by_parent[row["location_id"]].append(build_node(row))

    # Resolve NPC station / solar_system names via ESI /universe/names/
    name_ids = [lid for lid, info in location_groups.items() if info["location_type"] in ("station", "solar_system")]
    name_map = await resolve_entity_names(name_ids) if name_ids else {}

    result_tree = [
        {
            "location_id": loc_id,
            "location_type": info["location_type"],
            "location_name": name_map.get(loc_id, {}).get("name"),
            "items": info["items"],
        }
        for loc_id, info in location_groups.items()
    ]

    # Player structure names: read DB cache; queue Celery task for uncached IDs.
    if orphaned_by_parent:
        structure_ids = list(orphaned_by_parent.keys())
        cached_result = await db.execute(
            select(PlayerStructure).where(PlayerStructure.structure_id.in_(structure_ids))
        )
        cached_map: dict[int, str | None] = {r.structure_id: r.name for r in cached_result.scalars()}

        unknown_ids = [sid for sid in structure_ids if sid not in cached_map or cached_map[sid] is None]
        if unknown_ids:
            asyncio.create_task(asyncio.to_thread(
                celery_app.send_task,
                "app.tasks.characters.structures.resolve_player_structures",
                kwargs={"structure_ids": unknown_ids, "character_db_id": char.id},
            ))

        for structure_id, children in orphaned_by_parent.items():
            name = cached_map.get(structure_id)
            result_tree.append({
                "location_id": structure_id,
                "location_type": "station",
                "location_name": name or f"玩家建筑 #{structure_id}",
                "items": children,
            })

    # 按地点名称过滤
    if q:
        q_lower = q.strip().lower()
        result_tree = [
            loc for loc in result_tree
            if q_lower in (loc["location_name"] or "").lower()
            or q_lower in str(loc["location_id"])
        ]

    total = len(result_tree)
    start = (page - 1) * page_size
    paginated = result_tree[start : start + page_size]

    return {"total": total, "page": page, "page_size": page_size, "locations": paginated}


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
            "body": m.body,
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

    # If body is empty, trigger a background refresh
    if not mail.body:
        from app.tasks.characters.mail import fetch_mail_body
        fetch_mail_body.delay(char.id, mail_id)
        _logger.info("Triggered mail body refresh for character %d, mail %d", char.id, mail_id)

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
