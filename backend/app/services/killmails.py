"""Killmail valuation and detail formatting (ESI killmails are public + immutable)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.contracts import parse_dt
from app.services.esi_names import resolve_entity_names
from app.services.market import get_average_prices
from app.services.sde import resolve_type_names, type_icon_url


def _ship_render(type_id: int) -> str:
    return f"https://images.evetech.net/types/{type_id}/render?size=128"


def _walk_items(items: list[dict] | None, acc: list[dict]) -> None:
    """Flatten nested killmail items (containers) into a single list."""
    for it in items or []:
        acc.append(it)
        _walk_items(it.get("items"), acc)


def killmail_value(km: dict, prices: dict[int, float]) -> float:
    """Total destroyed+dropped value: victim ship hull + all (nested) items."""
    victim = km.get("victim", {}) or {}
    total = 0.0
    ship = victim.get("ship_type_id")
    if ship:
        total += prices.get(ship, 0.0)
    flat: list[dict] = []
    _walk_items(victim.get("items"), flat)
    for it in flat:
        tid = it.get("item_type_id")
        if not tid:
            continue
        qty = (it.get("quantity_destroyed") or 0) + (it.get("quantity_dropped") or 0)
        total += prices.get(tid, 0.0) * qty
    return total


async def build_summary(km: dict, character_eve_id: int, prices: dict[int, float]) -> dict:
    """Build a row payload for character_killmails from a full killmail dict."""
    victim = km.get("victim", {}) or {}
    attackers = km.get("attackers", []) or []
    return {
        "is_loss": victim.get("character_id") == character_eve_id,
        "ship_type_id": victim.get("ship_type_id"),
        "solar_system_id": km.get("solar_system_id"),
        "killmail_time": parse_dt(km.get("killmail_time")),
        "attacker_count": len(attackers),
        "total_value": killmail_value(km, prices),
    }


async def format_detail(
    km: dict, db: AsyncSession, locale: str = "en", total_value: float | None = None
) -> dict:
    """Resolve names/types and produce a structured detail payload for the UI.

    When `total_value` is provided (the value persisted at sync time), it is
    reused verbatim so the list and detail views never disagree, and the extra
    market-price round-trip is skipped.
    """
    victim = km.get("victim", {}) or {}
    attackers = km.get("attackers", []) or []

    # Gather IDs.
    entity_ids: list[int] = [km.get("solar_system_id")]
    type_ids: list[int] = []
    for who in [victim, *attackers]:
        entity_ids += [who.get("character_id"), who.get("corporation_id"), who.get("alliance_id")]
        type_ids += [who.get("ship_type_id")]
    for a in attackers:
        type_ids.append(a.get("weapon_type_id"))
    flat_items: list[dict] = []
    _walk_items(victim.get("items"), flat_items)
    type_ids += [it.get("item_type_id") for it in flat_items]

    entity_ids = [i for i in entity_ids if i]
    type_ids = [i for i in type_ids if i]
    name_map = await resolve_entity_names(entity_ids) if entity_ids else {}
    type_map = await resolve_type_names(type_ids, db, locale=locale) if type_ids else {}
    if total_value is None:
        total_value = killmail_value(km, await get_average_prices())

    def _en(i: int | None) -> str | None:
        return name_map.get(i, {}).get("name") if i else None

    def _tn(i: int | None) -> str | None:
        return type_map.get(i) if i else None

    items_out = []
    for it in flat_items:
        tid = it.get("item_type_id")
        items_out.append({
            "type_id": tid,
            "type_name": _tn(tid) or (f"类型 #{tid}" if tid else "—"),
            "icon_url": type_icon_url(tid) if tid else None,
            "dropped": it.get("quantity_dropped") or 0,
            "destroyed": it.get("quantity_destroyed") or 0,
        })

    attackers_out = [
        {
            "character_name": _en(a.get("character_id")),
            "corporation_name": _en(a.get("corporation_id")),
            "alliance_name": _en(a.get("alliance_id")),
            "ship_type_id": a.get("ship_type_id"),
            "ship_name": _tn(a.get("ship_type_id")),
            "ship_icon": type_icon_url(a.get("ship_type_id")) if a.get("ship_type_id") else None,
            "weapon_name": _tn(a.get("weapon_type_id")),
            "damage_done": a.get("damage_done", 0),
            "final_blow": a.get("final_blow", False),
            "security_status": a.get("security_status"),
        }
        for a in attackers
    ]
    attackers_out.sort(key=lambda x: (not x["final_blow"], -x["damage_done"]))

    ship_tid = victim.get("ship_type_id")
    return {
        "killmail_id": km.get("killmail_id"),
        "killmail_time": km.get("killmail_time"),
        "solar_system_id": km.get("solar_system_id"),
        "solar_system_name": _en(km.get("solar_system_id")),
        "total_value": total_value,
        "victim": {
            "character_name": _en(victim.get("character_id")),
            "corporation_name": _en(victim.get("corporation_id")),
            "alliance_name": _en(victim.get("alliance_id")),
            "ship_type_id": ship_tid,
            "ship_name": _tn(ship_tid),
            "ship_render": _ship_render(ship_tid) if ship_tid else None,
            "damage_taken": victim.get("damage_taken", 0),
            "items": items_out,
        },
        "attackers": attackers_out,
    }
