"""Resolve EVE mail body hyperlinks (showinfo:/contract:) into detailed data.

Mail bodies returned by ESI contain custom-scheme links, e.g.:
  - showinfo:47408//1042436073304   → type 47408, concrete item/structure 1042436073304
  - showinfo:587                     → just a type
  - contract:30000142//232254516     → contract 232254516 in solar system 30000142

This module parses such references and resolves them via ESI / SDE, applying the
project-wide Redis *logical expiration* cache strategy (see CLAUDE.md):
  - cache miss            → resolve synchronously, populate cache, return
  - fresh hit             → return cached data immediately
  - stale hit             → return cached data immediately + background refresh
                            (guarded by a distributed lock to avoid stampede)
"""
import asyncio
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import logical_get, logical_set, try_acquire_lock
from app.esi.client import get_esi_client
from app.models.character import Character
from app.models.sde import SDEType
from app.services.contracts import (
    CONTRACT_STATUS_LABELS as _CONTRACT_STATUS_LABELS,
    CONTRACT_TYPE_LABELS as _CONTRACT_TYPE_LABELS,
    fetch_contract_items,
)
from app.services.esi_names import resolve_entity_names
from app.services.sde import type_icon_url

logger = logging.getLogger(__name__)

LINK_TTL = 3600  # 1h logical expiration for resolved mail-link payloads

# Both player structures AND ordinary item instances live in the "spawned items"
# range (>= 1e12), so the numeric range alone CANNOT tell them apart. The real
# signal is the type's SDE category: Upwell structures are category 65.
_STRUCTURE_ID_MIN = 1_000_000_000_000
_STRUCTURE_CATEGORY_IDS = {65, 40}  # 65 = Structure (Upwell), 40 = Sovereignty Structures
# NPC station ID range (see esi-docs id-ranges).
_STATION_ID_MIN = 60_000_000
_STATION_ID_MAX = 64_000_000


_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_desc(text: str | None) -> str | None:
    """Strip EVE in-game markup (<br>, <color>, <a href=showinfo:...>, …) to plain text."""
    if not text:
        return None
    text = _BR_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    return text.strip() or None




def _parse_ref(ref: str) -> tuple[str, list[str]]:
    """Split "scheme:a//b" into ("scheme", ["a", "b"])."""
    if ":" not in ref:
        return "", []
    scheme, rest = ref.split(":", 1)
    args = [a for a in rest.split("//") if a != ""]
    return scheme.strip().lower(), args


async def resolve_mail_link(
    ref: str, char: Character, db: AsyncSession, locale: str = "en"
) -> dict[str, Any]:
    """Resolve a single mail-link reference, with logical-expiration caching."""
    cache_key = f"mail:link:{char.id}:{locale}:{ref}"

    data, is_stale = await logical_get(cache_key)
    if data is not None:
        if is_stale and await try_acquire_lock(cache_key):
            asyncio.create_task(_refresh(cache_key, ref, char, locale))
        return data

    result = await _resolve(ref, char, db, locale)
    # Only cache successful resolutions. Errors (not_found / no_access) may clear
    # up after the user re-authorizes scopes or gains structure access, so we
    # avoid pinning a stale failure for an hour.
    if result.get("error") is None:
        await logical_set(cache_key, result, LINK_TTL)
    return result


async def _refresh(cache_key: str, ref: str, char: Character, locale: str) -> None:
    """Background refresh: re-resolve and overwrite the cache entry."""
    from app.core.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await _resolve(ref, char, db, locale)
        if result.get("error") is None:
            await logical_set(cache_key, result, LINK_TTL)
    except Exception:
        logger.exception("Background refresh failed for mail link %s", ref)


async def _resolve(
    ref: str, char: Character, db: AsyncSession, locale: str
) -> dict[str, Any]:
    scheme, args = _parse_ref(ref)
    try:
        if scheme == "showinfo" and args:
            return await _resolve_showinfo(args, char, db, locale)
        if scheme == "contract" and len(args) >= 2:
            return await _resolve_contract(args, char, db, locale)
        if scheme in _UNSUPPORTED_SCHEMES:
            title, message = _UNSUPPORTED_SCHEMES[scheme]
            return _unsupported(title, message)
    except Exception:
        logger.exception("Failed to resolve mail link %s", ref)
        return _err("解析失败")
    return _err("不支持的链接类型")


# Schemes that carry no ESI-resolvable data — only meaningful inside the game
# client. We intercept them to show a clear explanation instead of a dead link.
_UNSUPPORTED_SCHEMES: dict[str, tuple[str, str]] = {
    "hypernet": ("HyperNet 报价", "该链接为游戏内 HyperNet（海波网）报价，ESI 不提供相关数据，请在游戏客户端中查看。"),
    "fitting": ("装配方案", "该链接为舰船装配方案，ESI 无法按链接解析，请在游戏客户端中查看。"),
    "bookmark": ("书签", "该链接为个人/军团书签，ESI 不提供数据，请在游戏客户端中查看。"),
    "fleet": ("舰队", "该链接为舰队邀请，ESI 不提供数据，请在游戏客户端中查看。"),
}


def _unsupported(title: str, message: str) -> dict[str, Any]:
    return {
        "kind": "unsupported", "title": title, "subtitle": None,
        "icon_url": None, "description": message, "error": "unsupported",
        "fields": [], "items": [],
    }


def _err(message: str) -> dict[str, Any]:
    return {
        "kind": "unknown", "title": message, "subtitle": None,
        "icon_url": None, "description": None, "error": message, "fields": [], "items": [],
    }


# --------------------------------------------------------------------------- #
# showinfo
# --------------------------------------------------------------------------- #
async def _type_meta(type_id: int, db: AsyncSession, locale: str) -> dict[str, Any]:
    """Fetch a type's localized name, description and category from SDE."""
    row = (await db.execute(
        select(SDEType.name, SDEType.description, SDEType.category_id)
        .where(SDEType.type_id == type_id)
    )).first()
    if row is None:
        return {"name": None, "description": None, "category_id": None}
    name = (row.name or {}).get(locale) or (row.name or {}).get("en")
    desc = (row.description or {}).get(locale) or (row.description or {}).get("en")
    return {"name": name, "description": _clean_desc(desc), "category_id": row.category_id}


async def _resolve_showinfo(
    args: list[str], char: Character, db: AsyncSession, locale: str
) -> dict[str, Any]:
    type_id = int(args[0])
    item_id = int(args[1]) if len(args) > 1 else None

    meta = await _type_meta(type_id, db, locale)
    type_name = meta["name"] or f"类型 #{type_id}"
    description = meta["description"]
    icon = type_icon_url(type_id, 64)
    is_structure_type = meta["category_id"] in _STRUCTURE_CATEGORY_IDS

    # showinfo on a type only → item type card.
    if item_id is None:
        return {
            "kind": "type", "title": type_name, "subtitle": "物品类型",
            "icon_url": icon, "description": description, "error": None,
            "fields": [{"label": "类型 ID", "value": str(type_id)}],
            "items": [],
        }

    esi = get_esi_client()

    # Player-owned Upwell structure — ONLY when the type is actually a structure.
    if is_structure_type and item_id >= _STRUCTURE_ID_MIN:
        base_fields = [
            {"label": "类型", "value": type_name},
            {"label": "建筑 ID", "value": str(item_id)},
        ]
        try:
            data = await esi.get(
                f"/universe/structures/{item_id}/",
                token=char.access_token, refresh_token=char.refresh_token,
                character_id=char.character_id,
            )
        except Exception:
            data = None
        if isinstance(data, dict):
            extra_map = await resolve_entity_names(
                [data.get("solar_system_id"), data.get("owner_id")]
            )
            sys_name = extra_map.get(data.get("solar_system_id"), {}).get("name")
            owner_name = extra_map.get(data.get("owner_id"), {}).get("name")
            return {
                "kind": "structure", "title": data.get("name") or type_name,
                "subtitle": type_name, "icon_url": icon, "description": None, "error": None,
                "fields": base_fields + [
                    {"label": "所在星系", "value": sys_name or "—"},
                    {"label": "所有者", "value": owner_name or "—"},
                ],
                "items": [],
            }
        # No access (403) or not found — show what we know.
        return {
            "kind": "structure", "title": type_name, "subtitle": "玩家建筑",
            "icon_url": icon, "description": None, "error": "no_access",
            "fields": base_fields + [
                {"label": "提示", "value": "无权访问该建筑详情（需停靠/访问权限）"},
            ],
            "items": [],
        }

    # NPC station — public, no auth required.
    if _STATION_ID_MIN <= item_id <= _STATION_ID_MAX:
        try:
            data = await esi.get(f"/universe/stations/{item_id}/")
        except Exception:
            data = None
        if isinstance(data, dict):
            extra_map = await resolve_entity_names([data.get("system_id")])
            sys_name = extra_map.get(data.get("system_id"), {}).get("name")
            return {
                "kind": "station", "title": data.get("name") or type_name,
                "subtitle": type_name, "icon_url": icon, "description": None, "error": None,
                "fields": [
                    {"label": "类型", "value": type_name},
                    {"label": "空间站 ID", "value": str(item_id)},
                    {"label": "所在星系", "value": sys_name or "—"},
                ],
                "items": [],
            }

    # Entity ranges (character / corporation / alliance) — resolvable via /universe/names/.
    if item_id < _STRUCTURE_ID_MIN:
        info = (await resolve_entity_names([item_id])).get(item_id)
        if info and info.get("category") != "unknown":
            return {
                "kind": "entity", "title": info.get("name") or type_name,
                "subtitle": type_name, "icon_url": icon, "description": None, "error": None,
                "fields": [
                    {"label": "类型", "value": type_name},
                    {"label": "类别", "value": info.get("category", "—")},
                    {"label": "ID", "value": str(item_id)},
                ],
                "items": [],
            }

    # Otherwise it's an ordinary item *instance* (e.g. a module in a contract /
    # inventory). Instance IDs are not publicly resolvable — show the type card.
    return {
        "kind": "item", "title": type_name, "subtitle": "物品",
        "icon_url": icon, "description": description, "error": None,
        "fields": [{"label": "类型 ID", "value": str(type_id)}],
        "items": [],
    }


# --------------------------------------------------------------------------- #
# contract
# --------------------------------------------------------------------------- #
async def _resolve_contract(
    args: list[str], char: Character, db: AsyncSession, locale: str
) -> dict[str, Any]:
    system_id = int(args[0])
    contract_id = int(args[1])

    sys_map = await resolve_entity_names([system_id])
    system_name = sys_map.get(system_id, {}).get("name") or f"星系 #{system_id}"

    esi = get_esi_client()
    scopes = set((char.scopes or "").split())

    # ESI has no "get contract by id" endpoint; the only way to read an arbitrary
    # contract is to find it in a list the character is party to. A contract may
    # be assigned to the character OR to their corporation, so we check both
    # (each gated by its own scope). Alliance-assigned contracts are NOT exposed
    # by ESI — there is no /alliances/{id}/contracts/ endpoint.
    match: dict | None = None
    source: str | None = None  # "character" | "corporation"

    async def _find_in(path: str) -> dict | None:
        try:
            contracts = await esi.get(
                path, token=char.access_token, refresh_token=char.refresh_token,
                character_id=char.character_id, paginate=True,
            )
        except Exception:
            return None
        if isinstance(contracts, list):
            return next((c for c in contracts if c.get("contract_id") == contract_id), None)
        return None

    if "esi-contracts.read_character_contracts.v1" in scopes:
        match = await _find_in(f"/characters/{char.character_id}/contracts/")
        if match is not None:
            source = "character"

    if match is None and char.corporation_id and "esi-contracts.read_corporation_contracts.v1" in scopes:
        match = await _find_in(f"/corporations/{char.corporation_id}/contracts/")
        if match is not None:
            source = "corporation"

    if match is None:
        # Tailor the hint to what's actually missing.
        if not scopes & {
            "esi-contracts.read_character_contracts.v1",
            "esi-contracts.read_corporation_contracts.v1",
        }:
            hint = "缺少合同读取授权，请重新登录以授予合同权限"
        else:
            hint = "未找到该合同（仅能查看你或你公司为当事人的合同；联盟合同 ESI 不提供，超过 30 天的已完成合同也不返回）"
        return {
            "kind": "contract", "title": f"合同 #{contract_id}",
            "subtitle": system_name, "icon_url": None, "description": None, "error": "not_found",
            "fields": [
                {"label": "合同 ID", "value": str(contract_id)},
                {"label": "所在星系", "value": system_name},
                {"label": "提示", "value": hint},
            ],
            "items": [],
        }

    # Resolve party names.
    party_ids = [match.get("issuer_id"), match.get("assignee_id"), match.get("acceptor_id")]
    party_map = await resolve_entity_names(party_ids)

    def _name(pid: int | None) -> str:
        if not pid:
            return "—"
        return party_map.get(pid, {}).get("name") or str(pid)

    ctype = match.get("type", "unknown")
    status = match.get("status", "")
    fields = [
        {"label": "类型", "value": _CONTRACT_TYPE_LABELS.get(ctype, ctype)},
        {"label": "状态", "value": _CONTRACT_STATUS_LABELS.get(status, status)},
        {"label": "发起人", "value": _name(match.get("issuer_id"))},
        {"label": "指定接收方", "value": _name(match.get("assignee_id"))},
        {"label": "所在星系", "value": system_name},
    ]
    if match.get("price"):
        fields.append({"label": "价格", "value": f"{match['price']:,.2f} ISK"})
    if match.get("reward"):
        fields.append({"label": "报酬", "value": f"{match['reward']:,.2f} ISK"})
    if match.get("collateral"):
        fields.append({"label": "抵押金", "value": f"{match['collateral']:,.2f} ISK"})
    if match.get("volume"):
        fields.append({"label": "体积", "value": f"{match['volume']:,.1f} m³"})
    if match.get("date_issued"):
        fields.append({"label": "发布时间", "value": str(match["date_issued"])})
    if match.get("date_expired"):
        fields.append({"label": "过期时间", "value": str(match["date_expired"])})

    # Contract item list — reuse the shared fetcher (same source the contract
    # was found in) so the mail-link card and the contracts endpoints stay in
    # lockstep on item shape, naming and sort order.
    items = await fetch_contract_items(char, contract_id, source or "character", db, locale=locale)

    title = match.get("title") or _CONTRACT_TYPE_LABELS.get(ctype, "合同")
    return {
        "kind": "contract", "title": title, "subtitle": system_name,
        "icon_url": None, "description": None, "error": None, "fields": fields, "items": items,
    }
