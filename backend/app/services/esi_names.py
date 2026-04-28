"""Bulk entity name resolution via ESI /universe/names/."""
import logging
import time

import httpx

logger = logging.getLogger(__name__)
ESI_NAMES_URL = "https://esi.evetech.net/latest/universe/names/"
_CACHE_TTL = 3600  # 1 hour

# id -> (name, category, expire_monotonic)
_cache: dict[int, tuple[str, str, float]] = {}

# sender_type values that ESI /universe/names/ cannot resolve
_SKIP_CATEGORIES = {"other"}


def _evict_expired() -> None:
    now = time.monotonic()
    expired = [k for k, v in _cache.items() if v[2] < now]
    for k in expired:
        del _cache[k]


async def resolve_entity_names(ids: list[int | None]) -> dict[int, dict]:
    """
    Resolve entity IDs to {"name": str, "category": str} via ESI /universe/names/.

    Accepts a flat list that may contain None values (they are filtered out).
    Uses an in-memory TTL cache to avoid redundant ESI calls.
    Missing or unresolvable IDs are omitted from the returned dict.
    """
    valid_ids = list({i for i in ids if i is not None and i > 0})
    if not valid_ids:
        return {}

    _evict_expired()
    now = time.monotonic()
    missing = [i for i in valid_ids if i not in _cache]

    if missing:
        # ESI accepts up to 1000 IDs per request
        chunks = [missing[i: i + 1000] for i in range(0, len(missing), 1000)]
        async with httpx.AsyncClient(timeout=15.0) as client:
            for chunk in chunks:
                try:
                    resp = await client.post(ESI_NAMES_URL, json=chunk)
                    if resp.status_code == 200:
                        for item in resp.json():
                            _cache[item["id"]] = (
                                item["name"],
                                item["category"],
                                now + _CACHE_TTL,
                            )
                    # 404 means ESI couldn't find some IDs — skip silently
                except Exception as exc:
                    logger.warning("ESI /universe/names/ request failed: %s", exc)

    return {
        i: {"name": _cache[i][0], "category": _cache[i][1]}
        for i in valid_ids
        if i in _cache
    }


async def enrich_entity_names(
    rows: list[dict],
    id_field: str,
    name_field: str,
    *,
    skip_types: set[str] | None = None,
    type_field: str | None = None,
) -> None:
    """
    Enrich rows in-place with a resolved entity name field.

    Args:
        rows: List of dicts to enrich.
        id_field: Key holding the entity ID.
        name_field: Key to write the resolved name string into.
        skip_types: If type_field is given, skip rows whose type_field value is in this set.
        type_field: Optional key holding the entity type (e.g. "sender_type").
    """
    ids = []
    for row in rows:
        eid = row.get(id_field)
        if eid is None:
            continue
        if type_field and skip_types and row.get(type_field) in skip_types:
            continue
        ids.append(eid)

    name_map = await resolve_entity_names(ids)
    for row in rows:
        eid = row.get(id_field)
        if eid is not None and eid in name_map:
            row[name_field] = name_map[eid]["name"]
        else:
            row.setdefault(name_field, None)
