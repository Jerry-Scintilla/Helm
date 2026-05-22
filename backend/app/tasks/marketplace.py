import asyncio

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.marketplace.refresh_marketplace_index")
def refresh_marketplace_index() -> dict:
    """Periodic beat task: rebuild the plugin marketplace index in Redis."""
    from app.plugins.marketplace import refresh_cache

    count = asyncio.run(refresh_cache())
    return {"refreshed": count}
