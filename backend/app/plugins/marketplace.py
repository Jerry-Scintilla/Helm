"""
Plugin marketplace: curated index from GitHub, enriched with live PyPI/TestPyPI metadata.

Caching follows the Redis logical-expiration strategy (see CLAUDE.md):
  cache key: marketplace:index   logical TTL = 6 h
  On stale hit: return immediately + spawn background rebuild.
  On cache miss: build synchronously, populate cache, return.

Discovery strategy:
  1. Fetch the curated index from GitHub (authoritative source).
  2. For entries missing version/author/description, fetch from the appropriate
     registry (PyPI or TestPyPI) based on the entry's `source` field.
  Note: PyPI XML-RPC search is deprecated and removed. Discovery is curated-only.
"""
import asyncio
import logging

import httpx

from app.cache import logical_get, logical_set, try_acquire_lock
from app.core.config import settings
from app.schemas.plugin import MarketplacePlugin

logger = logging.getLogger(__name__)

CACHE_KEY = "marketplace:index"
CACHE_TTL = 21600  # 6 hours

_PYPI_JSON = "https://pypi.org/pypi/{package}/json"
_TESTPYPI_JSON = "https://test.pypi.org/pypi/{package}/json"


async def _fetch_curated_index() -> list[dict]:
    url = settings.marketplace_index_url
    if not url:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.warning("Failed to fetch curated index from %s: %s", url, exc)
        return []


async def _fetch_package_metadata(package_name: str, source: str) -> dict | None:
    """Fetch package info from PyPI or TestPyPI JSON API."""
    url = (_TESTPYPI_JSON if source == "testpypi" else _PYPI_JSON).format(package=package_name)
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            info = r.json()["info"]
            return {
                "version": info.get("version"),
                "author": info.get("author") or info.get("maintainer") or "",
                "description": info.get("summary") or "",
                "homepage": info.get("home_page") or info.get("project_url"),
            }
    except Exception as exc:
        logger.debug("%s metadata fetch failed for %s: %s", source, package_name, exc)
        return None


async def _build_index() -> list[dict]:
    curated = await _fetch_curated_index()

    index: dict[str, dict] = {}
    for entry in curated:
        pkg = entry.get("package_name") or entry.get("name")
        if not pkg:
            continue
        source = entry.get("source", "pypi")
        index[pkg] = {
            "package_name": pkg,
            "display_name": entry.get("display_name") or pkg,
            "description": entry.get("description") or "",
            "author": entry.get("author") or "",
            "version": entry.get("version"),
            "tags": entry.get("tags") or [],
            "verified": bool(entry.get("verified", False)),
            "homepage": entry.get("homepage"),
            "source": source,
        }

    # Enrich entries missing metadata by querying the appropriate registry.
    needs_enrich = [pkg for pkg, entry in index.items() if not entry.get("version")]
    if needs_enrich:
        metas = await asyncio.gather(
            *[_fetch_package_metadata(pkg, index[pkg]["source"]) for pkg in needs_enrich],
            return_exceptions=True,
        )
        for pkg, meta in zip(needs_enrich, metas):
            if not meta or isinstance(meta, Exception):
                continue
            entry = index[pkg]
            if not entry.get("version"):
                entry["version"] = meta.get("version")
            if not entry.get("author"):
                entry["author"] = meta.get("author") or ""
            if not entry.get("description"):
                entry["description"] = meta.get("description") or ""
            if not entry.get("homepage"):
                entry["homepage"] = meta.get("homepage")

    return list(index.values())


async def _background_refresh() -> None:
    try:
        data = await _build_index()
        await logical_set(CACHE_KEY, data, CACHE_TTL)
        logger.info("Marketplace index refreshed: %d plugins", len(data))
    except Exception:
        logger.exception("Background marketplace refresh failed")


async def get_marketplace_index(installed_packages: set[str]) -> list[MarketplacePlugin]:
    """Return marketplace plugins using Redis logical expiration."""
    data, is_stale = await logical_get(CACHE_KEY)

    if data is None:
        data = await _build_index()
        await logical_set(CACHE_KEY, data, CACHE_TTL)
    elif is_stale:
        if await try_acquire_lock(CACHE_KEY, ttl=120):
            asyncio.create_task(_background_refresh())

    return [
        MarketplacePlugin(**entry, installed=entry["package_name"] in installed_packages)
        for entry in data
    ]


async def refresh_cache() -> int:
    """Explicitly rebuild the marketplace index. Returns plugin count."""
    data = await _build_index()
    await logical_set(CACHE_KEY, data, CACHE_TTL)
    logger.info("Marketplace index refreshed: %d plugins", len(data))
    return len(data)
