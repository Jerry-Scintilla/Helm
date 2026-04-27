"""
Plugin loader — Phase 1 skeleton.
Phase 3 will add: pip install, hot-swap, SSE events, Celery task registration.
"""
import importlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def load_plugins(app: "FastAPI") -> None:
    """
    Load enabled plugins from DB on startup.
    Phase 1: no plugins in DB yet, this is effectively a no-op.
    """
    try:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        # Import here to avoid circular imports at module level
        # Plugin model will be added in Phase 3
        logger.info("Plugin loader: no plugins installed (Phase 1 skeleton)")
    except Exception as exc:
        logger.warning("Plugin loader skipped: %s", exc)
