import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.esi import cache as esi_cache
from app.esi.oauth import refresh_access_token

ESI_BASE = "https://esi.evetech.net/latest"
logger = logging.getLogger(__name__)


@dataclass
class ESIResponse:
    """Response wrapper with cache metadata."""
    data: Any
    from_cache: bool
    is_stale: bool
    ttl_remaining: int


_token_persist_callbacks: list = []


def register_token_persist(callback) -> None:
    _token_persist_callbacks.append(callback)


def _trigger_async_refresh(cache_key: str, path: str, **kwargs) -> None:
    """Fire-and-forget async cache refresh, avoiding circular import."""
    try:
        from app.tasks.esi_cache.refresh import refresh_esi_cache
        refresh_esi_cache.delay(cache_key, path, **kwargs)
    except Exception:
        logger.exception("Failed to trigger async cache refresh for %s", cache_key)


class ESIClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client or httpx.AsyncClient(timeout=30.0)

    async def aclose(self):
        await self._client.aclose()

    async def get(
        self,
        path: str,
        *,
        token: str | None = None,
        refresh_token: str | None = None,
        character_id: int | None = None,
        params: dict | None = None,
        paginate: bool = False,
        _internal: bool = False,
    ) -> Any:
        """
        Perform a GET request against ESI.

        - Uses stale-while-revalidate: returns cached data immediately if stale,
          then triggers an async background refresh.
        - Automatically refreshes expired access tokens.
        - Retries on transient errors with exponential backoff (max 3 attempts).
        - Handles ESI error rate limiting (X-ESI-Error-Limit-Remain).
        - When paginate=True, fetches all pages and returns a combined list.

        Internal callers (e.g. background refresh tasks) should pass _internal=True
        to skip the stale-while-revalidate logic and get fresh data directly.
        """
        if paginate:
            return await self._get_all_pages(
                path, token=token, refresh_token=refresh_token,
                character_id=character_id, params=params,
                _internal=_internal,
            )
        return await self._get_single(
            path, token=token, refresh_token=refresh_token,
            character_id=character_id, params=params,
            _internal=_internal,
        )

    async def _get_single(
        self,
        path: str,
        *,
        token: str | None,
        refresh_token: str | None,
        character_id: int | None,
        params: dict | None,
        page: int | None = None,
        _internal: bool = False,
    ) -> Any:
        cache_key = self._cache_key(path, params, page)
        cached = await esi_cache.get_cached(cache_key)

        # Cache miss — fetch from ESI
        if cached is None:
            headers, req_params = self._build_headers_and_params(token, params, page, None)
            url = f"{ESI_BASE}{path}"
            data, ttl, new_etag = await self._request_with_retry(
                url, headers, req_params, None,
                refresh_token=refresh_token, character_id=character_id,
            )
            if data is not None:
                await esi_cache.set_cached(cache_key, data, ttl or 300, new_etag)
            return data

        cached_entry = cached

        # Internal callers: always fetch fresh
        if _internal:
            headers, req_params = self._build_headers_and_params(token, params, page, cached_entry.etag)
            url = f"{ESI_BASE}{path}"
            data, ttl, new_etag = await self._request_with_retry(
                url, headers, req_params, cached_entry.data,
                refresh_token=refresh_token, character_id=character_id,
            )
            if data is not None:
                await esi_cache.set_cached(cache_key, data, ttl or 300, new_etag)
            return data

        # Stale-while-revalidate: return cached data immediately, trigger async refresh
        if cached_entry.is_stale:
            lock_acquired = await esi_cache.acquire_refresh_lock(cache_key)
            if lock_acquired:
                _trigger_async_refresh(
                    cache_key, path,
                    token=token, refresh_token=refresh_token,
                    character_id=character_id, params=params,
                    paginate=False,
                )
            return cached_entry.data

        # Not stale — conditional request to ESI
        headers, req_params = self._build_headers_and_params(token, params, page, cached_entry.etag)
        url = f"{ESI_BASE}{path}"
        data, ttl, new_etag = await self._request_with_retry(
            url, headers, req_params, cached_entry.data,
            refresh_token=refresh_token, character_id=character_id,
        )
        if data is not None:
            await esi_cache.set_cached(cache_key, data, ttl or 300, new_etag)
        return data

    async def _get_all_pages(
        self,
        path: str,
        *,
        token: str | None,
        refresh_token: str | None,
        character_id: int | None,
        params: dict | None,
        _internal: bool = False,
    ) -> list:
        cache_key = self._cache_key(path, params, page=1)
        cached_pages, cached_etag, is_stale, _ = await esi_cache.get_cached_pages(cache_key)

        # Cache miss — fetch all pages
        if not cached_pages:
            return await self._fetch_all_pages(
                path, token=token, refresh_token=refresh_token,
                character_id=character_id, params=params,
            )

        # Internal callers: always fetch fresh
        if _internal:
            return await self._fetch_all_pages(
                path, token=token, refresh_token=refresh_token,
                character_id=character_id, params=params,
            )

        # Stale — return cached immediately, trigger async refresh
        if is_stale:
            lock_acquired = await esi_cache.acquire_refresh_lock(cache_key)
            if lock_acquired:
                _trigger_async_refresh(
                    cache_key, path,
                    token=token, refresh_token=refresh_token,
                    character_id=character_id, params=params,
                    paginate=True,
                )
            # Combine cached pages
            result = []
            for page_data in cached_pages:
                if isinstance(page_data, list):
                    result.extend(page_data)
                else:
                    result.append(page_data)
            return result

        # Not stale — conditional request on first page
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cached_etag:
            headers["If-None-Match"] = cached_etag

        url = f"{ESI_BASE}{path}"
        req_params = dict(params or {})
        req_params["page"] = "1"

        first_page, ttl, new_etag, total_pages = await self._request_with_retry_pages(
            url, headers, req_params, cached_pages[0] if cached_pages else None,
            refresh_token=refresh_token, character_id=character_id,
        )

        if first_page is None:
            return cached_pages or []

        if total_pages <= 1:
            await esi_cache.set_cached_pages(cache_key, [first_page], ttl or 300, new_etag)
            return first_page if isinstance(first_page, list) else [first_page]

        # Fetch remaining pages concurrently
        tasks = [
            self._get_single(
                path, token=token, refresh_token=refresh_token,
                character_id=character_id, params=params, page=p,
                _internal=True,
            )
            for p in range(2, total_pages + 1)
        ]
        rest = await asyncio.gather(*tasks)
        all_pages = [first_page] + rest

        result = []
        for page_data in all_pages:
            if isinstance(page_data, list):
                result.extend(page_data)
            else:
                result.append(page_data)

        await esi_cache.set_cached_pages(cache_key, all_pages, ttl or 300, new_etag)
        return result

    async def _fetch_all_pages(
        self,
        path: str,
        *,
        token: str | None,
        refresh_token: str | None,
        character_id: int | None,
        params: dict | None,
    ) -> list:
        """Fetch all pages from ESI without using cache."""
        cache_key = self._cache_key(path, params, page=1)
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = f"{ESI_BASE}{path}"
        req_params = dict(params or {})
        req_params["page"] = "1"

        first_page, ttl, new_etag, total_pages = await self._request_with_retry_pages(
            url, headers, req_params, None,
            refresh_token=refresh_token, character_id=character_id,
        )

        if first_page is None:
            return []

        if total_pages <= 1:
            await esi_cache.set_cached_pages(cache_key, [first_page], ttl or 300, new_etag)
            return first_page if isinstance(first_page, list) else [first_page]

        tasks = [
            self._get_single(
                path, token=token, refresh_token=refresh_token,
                character_id=character_id, params=params, page=p,
                _internal=True,
            )
            for p in range(2, total_pages + 1)
        ]
        rest = await asyncio.gather(*tasks)
        all_pages = [first_page] + rest

        result = []
        for page_data in all_pages:
            if isinstance(page_data, list):
                result.extend(page_data)
            else:
                result.append(page_data)

        await esi_cache.set_cached_pages(cache_key, all_pages, ttl or 300, new_etag)
        return result

    def _build_headers_and_params(
        self, token: str | None, params: dict | None, page: int | None, etag: str | None
    ) -> tuple[dict, dict]:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if etag:
            headers["If-None-Match"] = etag
        req_params = dict(params or {})
        if page is not None:
            req_params["page"] = str(page)
        return headers, req_params

    async def _request_with_retry(
        self, url, headers, params, cached_data, *, refresh_token, character_id, max_retries=3
    ) -> tuple[Any, int | None, str | None]:
        data, ttl, etag, _ = await self._request_with_retry_pages(
            url, headers, params, cached_data,
            refresh_token=refresh_token, character_id=character_id,
            max_retries=max_retries,
        )
        return data, ttl, etag

    async def _request_with_retry_pages(
        self, url, headers, params, cached_data, *, refresh_token, character_id, max_retries=3
    ) -> tuple[Any, int | None, str | None, int]:
        delay = 1.0
        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                resp = await self._client.get(url, headers=headers, params=params)
            except httpx.TransportError as exc:
                last_exc = exc
                await asyncio.sleep(delay)
                delay *= 2
                continue

            error_remain = int(resp.headers.get("X-ESI-Error-Limit-Remain", 100))
            if error_remain < 10:
                reset_seconds = int(resp.headers.get("X-ESI-Error-Limit-Reset", 30))
                logger.warning("ESI error limit low (%d), sleeping %ds", error_remain, reset_seconds)
                await asyncio.sleep(reset_seconds)

            if resp.status_code == 304:
                return cached_data, None, headers.get("If-None-Match"), 1

            if resp.status_code == 401 and refresh_token and character_id:
                try:
                    new_tokens = await refresh_access_token(refresh_token)
                    headers["Authorization"] = f"Bearer {new_tokens['access_token']}"
                    for cb in _token_persist_callbacks:
                        await cb(character_id, new_tokens["access_token"], new_tokens.get("refresh_token", refresh_token))
                    continue
                except Exception:
                    break

            if resp.status_code in (502, 503, 504):
                await asyncio.sleep(delay)
                delay *= 2
                continue

            resp.raise_for_status()

            ttl = self._parse_ttl(resp.headers.get("Cache-Control", ""))
            etag = resp.headers.get("ETag")
            total_pages = int(resp.headers.get("X-Pages", 1))

            return resp.json(), ttl, etag, total_pages

        if last_exc:
            raise last_exc
        return None, None, None, 1

    @staticmethod
    def _cache_key(path: str, params: dict | None, page: int | None) -> str:
        key = path
        if params:
            key += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        if page is not None:
            key += f"&page={page}"
        return key

    @staticmethod
    def _parse_ttl(cache_control: str) -> int:
        match = re.search(r"max-age=(\d+)", cache_control)
        return int(match.group(1)) if match else 300


_esi_client: ESIClient | None = None


def get_esi_client() -> ESIClient:
    global _esi_client
    if _esi_client is None:
        _esi_client = ESIClient()
    return _esi_client