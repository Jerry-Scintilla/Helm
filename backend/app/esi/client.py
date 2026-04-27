import asyncio
import logging
import re
from typing import Any

import httpx

from app.esi import cache as esi_cache
from app.esi.oauth import refresh_access_token

ESI_BASE = "https://esi.evetech.net/latest"
logger = logging.getLogger(__name__)

# Callbacks registered to persist refreshed tokens; set by the app on startup.
# Signature: async (character_id: int, access_token: str, refresh_token: str) -> None
_token_persist_callbacks: list = []


def register_token_persist(callback) -> None:
    _token_persist_callbacks.append(callback)


class ESIClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client or httpx.AsyncClient(timeout=30.0)

    async def aclose(self):
        await self._client.aclose()

    # ── Public API ────────────────────────────────────────────────────────────

    async def get(
        self,
        path: str,
        *,
        token: str | None = None,
        refresh_token: str | None = None,
        character_id: int | None = None,
        params: dict | None = None,
        paginate: bool = False,
    ) -> Any:
        """
        Perform a GET request against ESI.

        - Caches responses using ETag + Cache-Control TTL in Redis.
        - Automatically refreshes expired access tokens.
        - Retries on transient errors with exponential backoff (max 3 attempts).
        - Handles ESI error rate limiting (X-ESI-Error-Limit-Remain).
        - When paginate=True, fetches all pages and returns a combined list.
        """
        if paginate:
            return await self._get_all_pages(
                path, token=token, refresh_token=refresh_token,
                character_id=character_id, params=params,
            )
        return await self._get_single(
            path, token=token, refresh_token=refresh_token,
            character_id=character_id, params=params,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _get_single(
        self,
        path: str,
        *,
        token: str | None,
        refresh_token: str | None,
        character_id: int | None,
        params: dict | None,
        page: int | None = None,
    ) -> Any:
        cache_key = self._cache_key(path, params, page)
        cached_data, cached_etag = await esi_cache.get_cached(cache_key)

        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cached_etag:
            headers["If-None-Match"] = cached_etag

        req_params = dict(params or {})
        if page is not None:
            req_params["page"] = str(page)

        url = f"{ESI_BASE}{path}"
        data, ttl, new_etag = await self._request_with_retry(
            url, headers, req_params, cached_data,
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
    ) -> list:
        cache_key = self._cache_key(path, params, page=1)
        cached_data, cached_etag = await esi_cache.get_cached(cache_key)

        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cached_etag:
            headers["If-None-Match"] = cached_etag

        url = f"{ESI_BASE}{path}"
        req_params = dict(params or {})
        req_params["page"] = "1"

        first_page, ttl, new_etag, total_pages = await self._request_with_retry_pages(
            url, headers, req_params, cached_data,
            refresh_token=refresh_token, character_id=character_id,
        )

        if first_page is None:
            return cached_data or []

        await esi_cache.set_cached(cache_key, first_page, ttl or 300, new_etag)

        if total_pages <= 1:
            return first_page if isinstance(first_page, list) else [first_page]

        # Fetch remaining pages concurrently
        tasks = [
            self._get_single(
                path, token=token, refresh_token=refresh_token,
                character_id=character_id, params=params, page=p,
            )
            for p in range(2, total_pages + 1)
        ]
        rest = await asyncio.gather(*tasks)
        result = list(first_page) if isinstance(first_page, list) else [first_page]
        for page_data in rest:
            if isinstance(page_data, list):
                result.extend(page_data)
        return result

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

            # Handle ESI error rate limit
            error_remain = int(resp.headers.get("X-ESI-Error-Limit-Remain", 100))
            if error_remain < 10:
                reset_seconds = int(resp.headers.get("X-ESI-Error-Limit-Reset", 30))
                logger.warning("ESI error limit low (%d), sleeping %ds", error_remain, reset_seconds)
                await asyncio.sleep(reset_seconds)

            if resp.status_code == 304:
                return cached_data, None, headers.get("If-None-Match"), 1

            if resp.status_code == 401 and refresh_token and character_id:
                # Token expired — refresh and retry
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

            # Parse Cache-Control TTL
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


# Module-level singleton used by Celery tasks
_esi_client: ESIClient | None = None


def get_esi_client() -> ESIClient:
    global _esi_client
    if _esi_client is None:
        _esi_client = ESIClient()
    return _esi_client
