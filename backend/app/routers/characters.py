import asyncio
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.character import Character
from app.models.esi_data import (
    CharacterAsset, CharacterMail, CharacterSkill, CharacterWallet,
    CharacterWalletJournal, CharacterWalletTransaction, CharacterSkillQueue, CharacterNotification,
    CharacterContract, CharacterKillmail, PlayerStructure,
)
from app.models.user import User
from app.services.esi_names import enrich_entity_names, resolve_entity_names
from app.services.notifications import extract_notification_ids, render_notification_text
from app.services.sde import enrich_type_icons, enrich_type_names, enrich_type_names_all_locales, resolve_type_names
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

    # Batch fetch wallet balances (CharacterWallet.character_id is internal Character.id)
    internal_ids = [c.id for c in characters]
    wallet_result = await db.execute(
        select(CharacterWallet.character_id, CharacterWallet.balance)
        .where(CharacterWallet.character_id.in_(internal_ids))
    )
    wallet_map: dict[int, float | None] = {row.character_id: row.balance for row in wallet_result}

    return [
        {
            "character_id": c.character_id,
            "character_name": c.character_name,
            "corporation_id": c.corporation_id,
            "corporation_name": name_map.get(c.corporation_id, {}).get("name") if c.corporation_id else None,
            "alliance_id": c.alliance_id,
            "alliance_name": name_map.get(c.alliance_id, {}).get("name") if c.alliance_id else None,
            "is_primary": c.is_primary,
            "wallet_balance": wallet_map.get(c.id),
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


@router.get("/{character_id}/portrait")
async def get_portrait(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.esi.client import get_esi_client
    await _get_character_for_user(character_id, current_user, db)
    esi = get_esi_client()
    data = await esi.get(f"/characters/{character_id}/portrait/")
    return data or {}


@router.get("/{character_id}/wallet")
async def get_wallet(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.cache import WALLET_TTL, logical_get, logical_set, try_acquire_lock
    from app.tasks.characters.wallet import _update_wallet

    char = await _get_character_for_user(character_id, current_user, db)
    cache_key = f"wallet:balance:{char.id}"

    data, is_stale = await logical_get(cache_key)
    if data is not None:
        if is_stale and await try_acquire_lock(cache_key):
            asyncio.create_task(asyncio.to_thread(
                celery_app.send_task,
                "app.tasks.characters.wallet.update_wallet",
                args=[char.id],
                queue="characters",
            ))
        return data

    # Cache miss: try DB first
    result = await db.execute(select(CharacterWallet).where(CharacterWallet.character_id == char.id))
    wallet = result.scalar_one_or_none()

    if wallet is None:
        # First-ever fetch: block until we have real data
        char_db_id = char.id
        await _update_wallet(char)
        db.expire_all()
        result = await db.execute(select(CharacterWallet).where(CharacterWallet.character_id == char_db_id))
        wallet = result.scalar_one_or_none()

    payload = {
        "balance": wallet.balance if wallet else None,
        "updated_at": wallet.updated_at.isoformat() if wallet and wallet.updated_at else None,
    }
    await logical_set(cache_key, payload, WALLET_TTL)
    return payload


@router.post("/{character_id}/wallet/refresh")
async def refresh_wallet(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.cache import WALLET_TTL, logical_delete, logical_set
    from app.tasks.characters.wallet import _update_wallet
    from app.tasks.characters.wallet_journal import _update_wallet_journal
    from app.tasks.characters.wallet_transactions import _update_wallet_transactions

    char = await _get_character_for_user(character_id, current_user, db)
    char_db_id = char.id

    # Fetch all three concurrently from ESI; each writes to DB and invalidates its cache key
    await asyncio.gather(
        _update_wallet(char),
        _update_wallet_journal(char),
        _update_wallet_transactions(char),
    )

    # Re-read balance and rebuild balance cache
    db.expire_all()
    result = await db.execute(select(CharacterWallet).where(CharacterWallet.character_id == char_db_id))
    wallet = result.scalar_one_or_none()
    payload = {
        "balance": wallet.balance if wallet else None,
        "updated_at": wallet.updated_at.isoformat() if wallet and wallet.updated_at else None,
    }
    await logical_set(f"wallet:balance:{char_db_id}", payload, WALLET_TTL)
    return payload


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
    await enrich_type_icons(asset_rows, id_field="type_id", icon_field="icon_url", db=db)

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
            "icon_url": row.get("icon_url"),
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

    # 按地点名称或资产内容过滤
    if q:
        q_lower = q.strip().lower()

        def type_name_matches(type_name) -> bool:
            """type_name 为全语言字典 {"en": ..., "zh": ...}，任一语言命中即可。"""
            if not type_name:
                return False
            if isinstance(type_name, dict):
                return any(q_lower in str(v).lower() for v in type_name.values() if v)
            return q_lower in str(type_name).lower()

        def node_matches(node: dict) -> bool:
            """递归判断节点自身或其任意子项是否命中。"""
            if type_name_matches(node.get("type_name")):
                return True
            return any(node_matches(child) for child in node.get("items", []))

        def location_matches(loc: dict) -> bool:
            if q_lower in (loc["location_name"] or "").lower():
                return True
            if q_lower in str(loc["location_id"]):
                return True
            return any(node_matches(item) for item in loc["items"])

        result_tree = [loc for loc in result_tree if location_matches(loc)]

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


@router.get("/{character_id}/mail/resolve-link")
async def resolve_mail_link_endpoint(
    character_id: int,
    ref: str = Query(..., description="邮件正文链接引用，如 showinfo:47408//1042436073304 或 contract:30000142//232254516"),
    locale: str = Query("en", description="名称本地化语言"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    """解析邮件正文中的 showinfo:/contract: 超链接为详细数据（带 Redis 逻辑过期缓存）。"""
    char = await _get_character_for_user(character_id, current_user, db)
    from app.services.mail_links import resolve_mail_link
    return await resolve_mail_link(ref, char, db, locale=locale)


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
    from app.cache import WALLET_TTL, logical_get, logical_set, try_acquire_lock

    char = await _get_character_for_user(character_id, current_user, db)
    cache_key = f"wallet:journal:{char.id}:{page}:{per_page}"
    lock_key = f"wallet:journal-refresh:{char.id}"

    data, is_stale = await logical_get(cache_key)
    if data is not None:
        if is_stale and await try_acquire_lock(lock_key):
            asyncio.create_task(asyncio.to_thread(
                celery_app.send_task,
                "app.tasks.characters.wallet_journal.update_wallet_journal",
                args=[char.id],
                queue="characters",
            ))
        return data

    result = await db.execute(
        select(CharacterWalletJournal)
        .where(CharacterWalletJournal.character_id == char.id)
        .order_by(CharacterWalletJournal.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()

    if not entries and page == 1 and await try_acquire_lock(lock_key):
        asyncio.create_task(asyncio.to_thread(
            celery_app.send_task,
            "app.tasks.characters.wallet_journal.update_wallet_journal",
            args=[char.id],
            queue="characters",
        ))
        return []

    payload = [
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
    await logical_set(cache_key, payload, WALLET_TTL)
    return payload


@router.get("/{character_id}/wallet/transactions")
async def get_wallet_transactions(
    character_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.cache import WALLET_TTL, logical_get, logical_set, try_acquire_lock

    char = await _get_character_for_user(character_id, current_user, db)
    cache_key = f"wallet:tx:{char.id}:{page}:{per_page}"
    lock_key = f"wallet:tx-refresh:{char.id}"

    data, is_stale = await logical_get(cache_key)
    if data is not None:
        if is_stale and await try_acquire_lock(lock_key):
            asyncio.create_task(asyncio.to_thread(
                celery_app.send_task,
                "app.tasks.characters.wallet_transactions.update_wallet_transactions",
                args=[char.id],
                queue="characters",
            ))
        return data

    result = await db.execute(
        select(CharacterWalletTransaction)
        .where(CharacterWalletTransaction.character_id == char.id)
        .order_by(CharacterWalletTransaction.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()

    if not entries and page == 1 and await try_acquire_lock(lock_key):
        asyncio.create_task(asyncio.to_thread(
            celery_app.send_task,
            "app.tasks.characters.wallet_transactions.update_wallet_transactions",
            args=[char.id],
            queue="characters",
        ))
        return []

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
    await logical_set(cache_key, tx_rows, WALLET_TTL)
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
    notification_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)

    base_where = [CharacterNotification.character_id == char.id]
    if notification_type:
        base_where.append(CharacterNotification.type == notification_type)

    total_result = await db.execute(
        select(func.count()).select_from(CharacterNotification).where(*base_where)
    )
    total = total_result.scalar_one()

    stmt = (
        select(CharacterNotification)
        .where(*base_where)
        .order_by(CharacterNotification.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
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

    # Collect IDs from notification text bodies for inline resolution
    all_entity_ids: list[int] = []
    all_type_ids: list[int] = []
    for row in notif_rows:
        ent_ids, tp_ids = extract_notification_ids(row.get("text") or "")
        all_entity_ids.extend(ent_ids)
        all_type_ids.extend(tp_ids)

    entity_name_map = await resolve_entity_names(list(set(all_entity_ids))) if all_entity_ids else {}
    type_name_map = await resolve_type_names(list(set(all_type_ids)), db) if all_type_ids else {}

    for row in notif_rows:
        row["rendered_text"] = render_notification_text(
            row.get("text") or "", entity_name_map, type_name_map
        )

    return {"items": notif_rows, "total": total, "page": page, "page_size": page_size}


def _serialize_contract(c: CharacterContract) -> dict:
    return {
        "contract_id": c.contract_id,
        "source": c.source,
        "type": c.type,
        "status": c.status,
        "title": c.title,
        "for_corporation": c.for_corporation,
        "availability": c.availability,
        "issuer_id": c.issuer_id,
        "assignee_id": c.assignee_id,
        "acceptor_id": c.acceptor_id,
        "start_location_id": c.start_location_id,
        "end_location_id": c.end_location_id,
        "price": c.price,
        "reward": c.reward,
        "collateral": c.collateral,
        "buyout": c.buyout,
        "volume": c.volume,
        "days_to_complete": c.days_to_complete,
        "date_issued": c.date_issued,
        "date_expired": c.date_expired,
        "date_accepted": c.date_accepted,
        "date_completed": c.date_completed,
    }


CONTRACT_LIST_TTL = 600  # 10 min logical expiration


@router.get("/{character_id}/contracts")
async def get_contracts(
    character_id: int,
    direction: str = Query("all", description="all | outgoing | incoming"),
    contract_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.cache import logical_get, logical_set, try_acquire_lock

    char = await _get_character_for_user(character_id, current_user, db)
    cache_key = f"contracts:list:{char.id}:{direction}:{contract_type}:{status}:{page}:{per_page}"
    lock_key = f"contracts-refresh:{char.id}"

    data, is_stale = await logical_get(cache_key)
    if data is not None:
        if is_stale and await try_acquire_lock(lock_key):
            asyncio.create_task(asyncio.to_thread(
                celery_app.send_task,
                "app.tasks.characters.contracts.update_contracts",
                args=[char.id], queue="characters",
            ))
        return data

    conditions = [CharacterContract.character_id == char.id]
    if direction == "outgoing":
        conditions.append(CharacterContract.issuer_id == char.character_id)
    elif direction == "incoming":
        conditions.append(CharacterContract.issuer_id != char.character_id)
    if contract_type:
        conditions.append(CharacterContract.type == contract_type)
    if status:
        conditions.append(CharacterContract.status == status)

    total = (await db.execute(
        select(func.count()).select_from(CharacterContract).where(*conditions)
    )).scalar_one()

    rows = (await db.execute(
        select(CharacterContract)
        .where(*conditions)
        .order_by(CharacterContract.date_issued.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )).scalars().all()

    # First-ever load: queue a sync so data appears on the next poll.
    if total == 0 and page == 1 and await try_acquire_lock(lock_key):
        asyncio.create_task(asyncio.to_thread(
            celery_app.send_task,
            "app.tasks.characters.contracts.update_contracts",
            args=[char.id], queue="characters",
        ))

    items = [_serialize_contract(c) for c in rows]

    # Resolve party + location names (stations/systems via ESI; structures stay as ids).
    name_ids: list[int] = []
    for it in items:
        name_ids += [it["issuer_id"], it["assignee_id"], it["acceptor_id"],
                     it["start_location_id"], it["end_location_id"]]
    name_map = await resolve_entity_names(name_ids) if name_ids else {}

    def _nm(i: int | None) -> str | None:
        return name_map.get(i, {}).get("name") if i else None

    for it in items:
        it["issuer_name"] = _nm(it["issuer_id"])
        it["assignee_name"] = _nm(it["assignee_id"])
        it["acceptor_name"] = _nm(it["acceptor_id"])
        it["start_location_name"] = _nm(it["start_location_id"])
        it["end_location_name"] = _nm(it["end_location_id"])

    payload = {"total": total, "page": page, "per_page": per_page, "items": items}
    await logical_set(cache_key, payload, CONTRACT_LIST_TTL)
    return payload


@router.get("/{character_id}/contracts/{contract_id}")
async def get_contract_detail(
    character_id: int,
    contract_id: int,
    locale: str = Query("en"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.cache import logical_get, logical_set
    from app.services.contracts import fetch_contract_bids, fetch_contract_items

    char = await _get_character_for_user(character_id, current_user, db)
    contract = (await db.execute(
        select(CharacterContract).where(
            CharacterContract.character_id == char.id,
            CharacterContract.contract_id == contract_id,
        )
    )).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    base = _serialize_contract(contract)
    name_ids = [base["issuer_id"], base["assignee_id"], base["acceptor_id"],
                base["start_location_id"], base["end_location_id"]]
    name_map = await resolve_entity_names([i for i in name_ids if i])
    for key in ("issuer", "assignee", "acceptor", "start_location", "end_location"):
        eid = base[f"{key}_id"]
        base[f"{key}_name"] = name_map.get(eid, {}).get("name") if eid else None

    # Items/bids are immutable once the contract exists → lazy fetch + logical cache.
    cache_key = f"contracts:detail:{char.id}:{contract_id}:{locale}"
    cached, is_stale = await logical_get(cache_key)
    if cached is not None and not is_stale:
        base["items"] = cached.get("items", [])
        base["bids"] = cached.get("bids", [])
        return base

    items = await fetch_contract_items(char, contract_id, contract.source, db, locale=locale)
    bids = await fetch_contract_bids(char, contract_id, contract.source) if contract.type == "auction" else []
    await logical_set(cache_key, {"items": items, "bids": bids}, 86400)
    base["items"] = items
    base["bids"] = bids
    return base


KILLMAIL_LIST_TTL = 600  # 10 min logical expiration


@router.get("/{character_id}/killmails")
async def get_killmails(
    character_id: int,
    filter: str = Query("all", description="all | kills | losses"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.cache import logical_get, logical_set, try_acquire_lock

    char = await _get_character_for_user(character_id, current_user, db)
    cache_key = f"killmails:list:{char.id}:{filter}:{page}:{per_page}"
    lock_key = f"killmails-refresh:{char.id}"

    data, is_stale = await logical_get(cache_key)
    if data is not None:
        if is_stale and await try_acquire_lock(lock_key):
            asyncio.create_task(asyncio.to_thread(
                celery_app.send_task,
                "app.tasks.characters.killmails.update_killmails",
                args=[char.id], queue="characters",
            ))
        return data

    conditions = [CharacterKillmail.character_id == char.id]
    if filter == "kills":
        conditions.append(CharacterKillmail.is_loss == False)  # noqa: E712
    elif filter == "losses":
        conditions.append(CharacterKillmail.is_loss == True)  # noqa: E712

    total = (await db.execute(
        select(func.count()).select_from(CharacterKillmail).where(*conditions)
    )).scalar_one()

    rows = (await db.execute(
        select(CharacterKillmail)
        .where(*conditions)
        .order_by(CharacterKillmail.killmail_time.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )).scalars().all()

    if total == 0 and page == 1 and await try_acquire_lock(lock_key):
        asyncio.create_task(asyncio.to_thread(
            celery_app.send_task,
            "app.tasks.characters.killmails.update_killmails",
            args=[char.id], queue="characters",
        ))

    items = [
        {
            "killmail_id": k.killmail_id,
            "is_loss": k.is_loss,
            "ship_type_id": k.ship_type_id,
            "ship_icon": f"https://images.evetech.net/types/{k.ship_type_id}/icon?size=64" if k.ship_type_id else None,
            "solar_system_id": k.solar_system_id,
            "killmail_time": k.killmail_time,
            "attacker_count": k.attacker_count,
            "total_value": k.total_value,
        }
        for k in rows
    ]

    ship_ids = [it["ship_type_id"] for it in items if it["ship_type_id"]]
    sys_ids = [it["solar_system_id"] for it in items if it["solar_system_id"]]
    ship_names = await resolve_type_names(ship_ids, db, locale="en") if ship_ids else {}
    sys_map = await resolve_entity_names(sys_ids) if sys_ids else {}
    for it in items:
        it["ship_name"] = ship_names.get(it["ship_type_id"])
        it["solar_system_name"] = sys_map.get(it["solar_system_id"], {}).get("name") if it["solar_system_id"] else None

    payload = {"total": total, "page": page, "per_page": per_page, "items": items}
    await logical_set(cache_key, payload, KILLMAIL_LIST_TTL)
    return payload


@router.get("/{character_id}/killmails/{killmail_id}")
async def get_killmail_detail(
    character_id: int,
    killmail_id: int,
    locale: str = Query("en"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    from app.cache import logical_get, logical_set
    from app.esi.client import get_esi_client
    from app.services.killmails import format_detail

    char = await _get_character_for_user(character_id, current_user, db)
    row = (await db.execute(
        select(CharacterKillmail).where(
            CharacterKillmail.character_id == char.id,
            CharacterKillmail.killmail_id == killmail_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Killmail not found")

    # Killmails are immutable → cache the formatted detail aggressively.
    cache_key = f"killmails:detail:{killmail_id}:{locale}"
    cached, is_stale = await logical_get(cache_key)
    if cached is not None and not is_stale:
        return cached

    esi = get_esi_client()
    km = await esi.get(f"/killmails/{killmail_id}/{row.killmail_hash}/")
    if not isinstance(km, dict):
        raise HTTPException(status_code=502, detail="Failed to load killmail from ESI")
    detail = await format_detail(km, db, locale=locale)
    await logical_set(cache_key, detail, 604800)  # 7 days
    return detail


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
