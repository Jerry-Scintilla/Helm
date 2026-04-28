"""SDE type info lookup utilities with multi-language support."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sde import SDEType


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
