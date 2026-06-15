"""SDE type info lookup utilities with multi-language support."""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.esi.cache import acquire_refresh_lock, get_cached, set_cached
from app.models.sde import SDEType

_ICON_TTL = 86400  # 24h logical TTL for type icon cache entries


async def resolve_type_names(
    type_ids: list[int],
    db: AsyncSession,
    locale: str = "en",
) -> dict[int, str | None]:
    """
    Batch query type_id -> localized name from sde_type.

    Returns a dict mapping each type_id to its name in the specified locale
    (or None if not found). Falls back to "en" if the locale is missing.

    Args:
        type_ids: List of type IDs to resolve.
        db: AsyncSession instance.
        locale: Language code (e.g. "en", "zh", "de"). Defaults to "en".
    """
    if not type_ids:
        return {}

    unique_ids = list(set(type_ids))
    result = await db.execute(
        select(SDEType.type_id, SDEType.name).where(SDEType.type_id.in_(unique_ids))
    )
    name_map: dict[int, str | None] = {}
    for row in result.fetchall():
        name_dict: dict = row[1] or {}
        name_map[row[0]] = name_dict.get(locale) or name_dict.get("en")
    return name_map


async def resolve_type_names_all_locales(
    type_ids: list[int],
    db: AsyncSession,
) -> dict[int, dict | None]:
    """
    Batch query type_id -> full name dict (all locales) from sde_type.

    Returns a dict mapping each type_id to its complete name dict
    (e.g. {"en": "Gunnery V", "zh": "炮术 V"}) or None if not found.
    """
    if not type_ids:
        return {}

    unique_ids = list(set(type_ids))
    result = await db.execute(
        select(SDEType.type_id, SDEType.name).where(SDEType.type_id.in_(unique_ids))
    )
    return {row[0]: row[1] for row in result.fetchall()}


async def enrich_type_names(
    rows: list[dict],
    id_field: str,
    name_field: str = "type_name",
    locale: str = "en",
    db: AsyncSession | None = None,
) -> list[dict]:
    """
    Enrich a list of row dicts with a resolved localized type name field.

    Args:
        rows: List of dicts, each containing id_field (e.g. "type_id" or "skill_id")
        id_field: Key in each row holding the type_id value
        name_field: Output key name for the resolved name (default: "type_name")
        locale: Language code (e.g. "en", "zh"). Defaults to "en".
        db: AsyncSession instance (optional, caller can pass None and call enrich inline)

    Returns rows with name_field added as a localized string.
    """
    if not rows:
        return rows

    ids = [r[id_field] for r in rows if r.get(id_field)]
    if not ids:
        return rows

    if db is None:
        for row in rows:
            row[name_field] = None
        return rows

    name_map = await resolve_type_names(ids, db, locale=locale)
    for row in rows:
        type_id = row.get(id_field)
        row[name_field] = name_map.get(type_id) if type_id is not None else None
    return rows


async def enrich_type_names_all_locales(
    rows: list[dict],
    id_field: str,
    name_field: str = "type_name",
    db: AsyncSession | None = None,
) -> list[dict]:
    """
    Enrich a list of row dicts with a resolved type name field containing ALL locales.

    Args:
        rows: List of dicts, each containing id_field (e.g. "type_id" or "skill_id")
        id_field: Key in each row holding the type_id value
        name_field: Output key name for the resolved name (default: "type_name")
        db: AsyncSession instance (optional)

    Returns rows with name_field added as a dict with all available locales
    (e.g. {"en": "Gunnery V", "zh": "炮术 V"}).
    """
    if not rows:
        return rows

    ids = [r[id_field] for r in rows if r.get(id_field)]
    if not ids:
        return rows

    if db is None:
        for row in rows:
            row[name_field] = None
        return rows

    name_map = await resolve_type_names_all_locales(ids, db)
    for row in rows:
        type_id = row.get(id_field)
        row[name_field] = name_map.get(type_id) if type_id is not None else None
    return rows


def type_icon_url(type_id: int, size: int = 32) -> str:
    """Shared evetech.net type-icon URL builder (single source of truth)."""
    return f"https://images.evetech.net/types/{type_id}/icon?size={size}"


def _icon_url(type_id: int) -> str:
    return type_icon_url(type_id)


async def resolve_type_icons_cached(
    type_ids: list[int],
    db: AsyncSession,
) -> dict[int, str | None]:
    """
    Return {type_id: icon_url} using Redis logical expiration cache.

    Cache miss  → batch query SDE DB, populate cache, return URLs.
    Fresh hit   → return cached URL immediately.
    Stale hit   → return cached URL immediately, trigger background Celery refresh.
    Unknown IDs (not in SDE) → mapped to None, not cached.
    """
    if not type_ids:
        return {}

    unique_ids = list(set(type_ids))
    result: dict[int, str | None] = {}
    missing: list[int] = []
    stale: list[int] = []

    for type_id in unique_ids:
        entry = await get_cached(f"sde:type_icons:{type_id}")
        if entry is None:
            missing.append(type_id)
        elif entry.is_stale:
            result[type_id] = entry.data.get("icon_url")
            stale.append(type_id)
        else:
            result[type_id] = entry.data.get("icon_url")

    if missing:
        rows = await db.execute(
            select(SDEType.type_id).where(SDEType.type_id.in_(missing))
        )
        found_ids = {row[0] for row in rows.fetchall()}
        for type_id in missing:
            if type_id in found_ids:
                url = _icon_url(type_id)
                await set_cached(f"sde:type_icons:{type_id}", {"icon_url": url}, ttl=_ICON_TTL)
                result[type_id] = url
            else:
                result[type_id] = None

    for type_id in stale:
        if await acquire_refresh_lock(f"sde:type_icons:{type_id}"):
            asyncio.create_task(asyncio.to_thread(
                _dispatch_icon_refresh, type_id
            ))

    return result


def _dispatch_icon_refresh(type_id: int) -> None:
    from app.tasks.celery_app import celery_app
    celery_app.send_task(
        "app.tasks.sde.refresh_icon_cache.refresh_type_icon_cache",
        kwargs={"type_id": type_id},
    )


async def enrich_type_icons(
    rows: list[dict],
    id_field: str = "type_id",
    icon_field: str = "icon_url",
    db: AsyncSession | None = None,
) -> list[dict]:
    """
    Enrich row dicts with icon_url from the cached icon service.
    Mirrors enrich_type_names_all_locales in structure.
    """
    if not rows or db is None:
        for row in rows:
            row[icon_field] = None
        return rows

    ids = [r[id_field] for r in rows if r.get(id_field) is not None]
    if not ids:
        return rows

    icon_map = await resolve_type_icons_cached(ids, db)
    for row in rows:
        type_id = row.get(id_field)
        row[icon_field] = icon_map.get(type_id) if type_id is not None else None
    return rows
