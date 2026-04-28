"""
Plugin loader — runs at application startup via lifespan.
Loads all enabled plugins from the database and mounts their routers.
"""
import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.plugin import Plugin
from app.plugins.events import start_listener
from app.plugins.installer import load_plugin_class
from app.plugins.manager import _mount_router, _register_celery_tasks, _validate_plugin, set_app
from app.plugins.registry import registry

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def load_plugins(app: "FastAPI") -> None:
    set_app(app)
    await start_listener()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Plugin).where(Plugin.is_enabled == True, Plugin.status == "enabled")
        )
        plugins = result.scalars().all()

    for db_plugin in plugins:
        try:
            plugin_class = load_plugin_class(db_plugin.entry_point)
            _validate_plugin(plugin_class)
            plugin_instance = plugin_class()
            registry.register(plugin_instance)
            _mount_router(plugin_instance)
            _register_celery_tasks(plugin_instance)
            logger.info("Loaded plugin '%s' v%s", db_plugin.name, db_plugin.version)
        except Exception as exc:
            logger.error("Failed to load plugin '%s': %s", db_plugin.name, exc)
            async with AsyncSessionLocal() as db:
                err_plugin = (await db.execute(
                    select(Plugin).where(Plugin.name == db_plugin.name)
                )).scalar_one_or_none()
                if err_plugin:
                    err_plugin.status = "error"
                    err_plugin.error_message = str(exc)
                    await db.commit()
