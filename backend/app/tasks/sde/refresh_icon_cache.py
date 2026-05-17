import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.esi.cache import release_refresh_lock, set_cached
from app.models.sde import SDEType
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)

_ICON_TTL = 86400


@celery_app.task(
    name="app.tasks.sde.refresh_icon_cache.refresh_type_icon_cache",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def refresh_type_icon_cache(type_id: int) -> None:
    async def _run() -> None:
        try:
            async with AsyncSessionLocal() as db:
                row = await db.scalar(
                    select(SDEType.type_id).where(SDEType.type_id == type_id)
                )
            if row is not None:
                icon_url = f"https://images.evetech.net/types/{type_id}/icon?size=32"
                await set_cached(
                    f"sde:type_icons:{type_id}",
                    {"icon_url": icon_url},
                    ttl=_ICON_TTL,
                )
        except Exception:
            logger.exception("Failed to refresh icon cache for type_id=%d", type_id)
            raise
        finally:
            await release_refresh_lock(f"sde:type_icons:{type_id}")

    run_async(_run())
