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
from packaging.version import InvalidVersion, Version

from app.cache import logical_get, logical_set, try_acquire_lock
from app.core.config import settings
from app.schemas.plugin import MarketplacePlugin

logger = logging.getLogger(__name__)

CACHE_KEY = "marketplace:index"
CACHE_TTL = 21600  # 6 hours

# Per-package version list (resolved from the registry, not the curated index).
# The "v2" namespace invalidates the old cache shape (a plain list[str]); the
# value is now a list of version-metadata dicts.
VERSIONS_CACHE_KEY = "marketplace:versions:v2:{source}:{package}"
VERSIONS_CACHE_TTL = 3600  # 1 hour

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


def _sort_version_entries(entries: list[dict]) -> list[dict]:
    """Newest first. PEP 440-parseable versions sorted by Version; the rest
    (unparseable tags) appended after, string-sorted descending."""
    parseable: list[tuple[Version, dict]] = []
    other: list[dict] = []
    for e in entries:
        try:
            parseable.append((Version(e["version"]), e))
        except InvalidVersion:
            other.append(e)
    parseable.sort(key=lambda t: t[0], reverse=True)
    other.sort(key=lambda e: e["version"], reverse=True)
    return [e for _, e in parseable] + other


def _release_date(files: list) -> str | None:
    """Earliest upload timestamp (ISO 8601) across a release's files."""
    times = [
        f.get("upload_time_iso_8601")
        for f in files
        if isinstance(f, dict) and f.get("upload_time_iso_8601")
    ]
    return min(times) if times else None


async def _fetch_registry_versions(package_name: str, source: str) -> list[dict]:
    """All published versions for a package from the PyPI/TestPyPI JSON API.

    Returns one dict per version: ``{version, released_at, yanked,
    yanked_reason}``, newest first. Empty-distribution releases are skipped;
    fully-yanked releases are kept but flagged. Unknown package → empty list.
    """
    url = (_TESTPYPI_JSON if source == "testpypi" else _PYPI_JSON).format(package=package_name)
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url)
            if r.status_code == 404:
                return []
            r.raise_for_status()
            releases = r.json().get("releases", {}) or {}
    except Exception as exc:
        logger.debug("%s version fetch failed for %s: %s", source, package_name, exc)
        return []

    entries: list[dict] = []
    for ver, files in releases.items():
        if not isinstance(files, list) or not files:
            # Release with no uploaded distributions — can't be pip-installed.
            continue
        yanked = all(f.get("yanked") for f in files)
        yanked_reason = next(
            (f.get("yanked_reason") for f in files if f.get("yanked") and f.get("yanked_reason")),
            None,
        )
        entries.append({
            "version": ver,
            "released_at": _release_date(files),
            "yanked": yanked,
            "yanked_reason": yanked_reason,
        })
    return _sort_version_entries(entries)


async def get_plugin_versions(package_name: str, source: str = "pypi") -> list[dict]:
    """Available versions (with metadata) for a package, newest first.

    Uses the Redis logical-expiration cache strategy.
    """
    key = VERSIONS_CACHE_KEY.format(source=source, package=package_name)
    data, is_stale = await logical_get(key)

    if data is None:
        data = await _fetch_registry_versions(package_name, source)
        await logical_set(key, data, VERSIONS_CACHE_TTL)
    elif is_stale:
        if await try_acquire_lock(key, ttl=60):
            asyncio.create_task(_refresh_versions(key, package_name, source))

    return data


async def _refresh_versions(key: str, package_name: str, source: str) -> None:
    try:
        data = await _fetch_registry_versions(package_name, source)
        await logical_set(key, data, VERSIONS_CACHE_TTL)
    except Exception:
        logger.exception("Background version refresh failed for %s", package_name)


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


def _is_update_available(installed_version: str | None, market_version: str | None) -> bool:
    """True when both versions parse and the marketplace version is strictly newer.

    Unparseable versions are treated conservatively as "no update" so we never
    nag the user to "update" to a version we can't actually compare.
    """
    if not installed_version or not market_version:
        return False
    try:
        return Version(market_version) > Version(installed_version)
    except InvalidVersion:
        return False


async def get_marketplace_index(
    installed_versions: dict[str, str],
) -> list[MarketplacePlugin]:
    """Return marketplace plugins using Redis logical expiration.

    ``installed_versions`` maps package_name -> locally installed version so the
    index can flag both installation status and whether an update is available.
    """
    data, is_stale = await logical_get(CACHE_KEY)

    if data is None:
        data = await _build_index()
        await logical_set(CACHE_KEY, data, CACHE_TTL)
    elif is_stale:
        if await try_acquire_lock(CACHE_KEY, ttl=120):
            asyncio.create_task(_background_refresh())

    result = []
    for entry in data:
        pkg = entry["package_name"]
        installed_version = installed_versions.get(pkg)
        result.append(
            MarketplacePlugin(
                **entry,
                installed=pkg in installed_versions,
                installed_version=installed_version,
                update_available=_is_update_available(installed_version, entry.get("version")),
            )
        )
    return result


async def refresh_cache() -> int:
    """Explicitly rebuild the marketplace index. Returns plugin count."""
    data = await _build_index()
    await logical_set(CACHE_KEY, data, CACHE_TTL)
    logger.info("Marketplace index refreshed: %d plugins", len(data))
    return len(data)
