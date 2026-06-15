"""Shared contract helpers used by both the contracts module and mail-link cards.

Centralises the ESI ↔ display mapping (type/status labels) and the lazy fetch of
a contract's items / bids, so the mail-link resolver and the dedicated contracts
endpoints stay consistent.
"""
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.esi.client import get_esi_client
from app.models.character import Character
from app.services.sde import resolve_type_names, type_icon_url

CONTRACT_TYPE_LABELS = {
    "item_exchange": "物品交换",
    "auction": "拍卖",
    "courier": "快递",
    "loan": "贷款",
    "unknown": "未知",
}
CONTRACT_STATUS_LABELS = {
    "outstanding": "未完成",
    "in_progress": "进行中",
    "finished_issuer": "已完成（发起方）",
    "finished_contractor": "已完成（承接方）",
    "finished": "已完成",
    "cancelled": "已取消",
    "rejected": "已拒绝",
    "failed": "已失败",
    "deleted": "已删除",
    "reversed": "已撤销",
}


def parse_dt(value: Any) -> datetime | None:
    """Parse an ESI ISO-8601 timestamp into an aware datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _items_path(char: Character, contract_id: int, source: str) -> str:
    if source == "corporation" and char.corporation_id:
        return f"/corporations/{char.corporation_id}/contracts/{contract_id}/items/"
    return f"/characters/{char.character_id}/contracts/{contract_id}/items/"


async def fetch_contract_items(
    char: Character, contract_id: int, source: str, db: AsyncSession, locale: str = "en"
) -> list[dict]:
    """Fetch and format a contract's item list (item names resolved via SDE)."""
    esi = get_esi_client()
    try:
        raw = await esi.get(
            _items_path(char, contract_id, source),
            token=char.access_token, refresh_token=char.refresh_token,
            character_id=char.character_id,
        )
    except Exception:
        return []
    if not isinstance(raw, list) or not raw:
        return []

    type_ids = [it["type_id"] for it in raw if it.get("type_id")]
    name_map = await resolve_type_names(type_ids, db, locale=locale)
    items: list[dict] = []
    for it in raw:
        tid = it.get("type_id")
        items.append({
            "type_id": tid,
            "type_name": name_map.get(tid) or f"类型 #{tid}",
            "quantity": it.get("quantity"),
            "is_included": it.get("is_included", True),
            "is_singleton": it.get("is_singleton", False),
            "icon_url": type_icon_url(tid) if tid else None,
        })
    # Offered items first (included), then requested items.
    items.sort(key=lambda x: (not x["is_included"], x["type_name"]))
    return items


async def fetch_contract_bids(char: Character, contract_id: int, source: str) -> list[dict]:
    """Fetch auction bids for a contract (best-effort)."""
    esi = get_esi_client()
    if source == "corporation" and char.corporation_id:
        path = f"/corporations/{char.corporation_id}/contracts/{contract_id}/bids/"
    else:
        path = f"/characters/{char.character_id}/contracts/{contract_id}/bids/"
    try:
        raw = await esi.get(
            path, token=char.access_token, refresh_token=char.refresh_token,
            character_id=char.character_id,
        )
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    raw.sort(key=lambda b: b.get("amount", 0), reverse=True)
    return raw
