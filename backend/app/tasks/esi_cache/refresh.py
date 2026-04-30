"""Background task to refresh stale ESI cache entries (stale-while-revalidate)."""
import logging

from app.esi import cache as esi_cache
from app.esi.client import get_esi_client
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)


def _build_refresh_params(kwargs: dict) -> dict:
    """Extract ESI get() kwargs from task payload."""
    return {
        "token": kwargs.get("token"),
        "refresh_token": kwargs.get("refresh_token"),
        "character_id": kwargs.get("character_id"),
        "params": kwargs.get("params"),
        "paginate": kwargs.get("paginate", False),
    }


@celery_app.task(
    name="app.tasks.esi_cache.refresh.refresh_esi_cache",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def refresh_esi_cache(self, cache_key: str, path: str, **esi_kwargs) -> None:
    """
    Refresh a stale ESI cache entry in the background.

    Args:
        cache_key: The cache key (without 'esi:cache:' prefix)
        path: ESI endpoint path (e.g. '/characters/123/skills/')
        **esi_kwargs: Forwarded to ESIClient.get()
    """
    async def _run():
        try:
            esi = get_esi_client()
            refresh_params = _build_refresh_params(esi_kwargs)

            # Fetch fresh data from ESI using _internal to skip stale-while-revalidate logic
            data = await esi.get(path, **refresh_params, _internal=True)

            # Determine TTL from central config
            ttl = esi_cache.get_ttl_for_path(path)

            if refresh_params.get("paginate"):
                await esi_cache.set_cached_pages(cache_key, data, ttl)
            else:
                await esi_cache.set_cached(cache_key, data, ttl)

            logger.info("ESI cache refreshed: %s", cache_key)

        except Exception:
            logger.exception("Failed to refresh ESI cache: %s", cache_key)
            raise
        finally:
            await esi_cache.release_refresh_lock(cache_key)

    run_async(_run())