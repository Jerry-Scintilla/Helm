"""
Plugin loader — runs at application startup via lifespan.
Loads all enabled plugins from the database and mounts their routers.
"""
import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.plugin import Plugin
from app.plugins.base import PluginContext
from app.plugins.events import start_listener
from app.plugins.installer import load_plugin_class
from app.plugins.manager import _mount_router, _publish_plugin_schedules, _register_celery_tasks, _serialize_character_submodules, _validate_plugin, set_app
from app.tasks.plugin_schedules import serialize_plugin_beat_schedule
from app.plugins.registry import extension_registry, registry

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def load_plugins(app: "FastAPI") -> None:
    logger.debug("load_plugins() BEGIN")
    set_app(app)
    await start_listener()

    async with AsyncSessionLocal() as db:
        # 加载所有 enabled 的插件，包括 status='error' 的（错误可能已修复）
        result = await db.execute(
            select(Plugin).where(
                Plugin.is_enabled == True,
                Plugin.status.in_(["enabled", "error"])
            )
        )
        plugins = result.scalars().all()
        logger.debug("DB query returned %d plugins: %s", len(plugins), [p.name for p in plugins])

        # 也查一下所有插件的状态
        all_result = await db.execute(select(Plugin))
        all_plugins = all_result.scalars().all()
        logger.debug("ALL plugins in DB: %s", [(p.name, p.is_enabled, p.status, getattr(p, 'error_message', None)) for p in all_plugins])

    for db_plugin in plugins:
        try:
            plugin_class = load_plugin_class(db_plugin.entry_point)
            _validate_plugin(plugin_class)
            plugin_instance = plugin_class()
            registry.register(plugin_instance)
            _mount_router(plugin_instance)
            _register_celery_tasks(plugin_instance)
            # Re-push Beat schedules so Beat self-heals even if Redis was flushed.
            await _publish_plugin_schedules(plugin_instance)

            # 调用 on_enable 生命周期钩子
            ctx = PluginContext(db_session_factory=AsyncSessionLocal)
            try:
                logger.debug("Calling on_enable for plugin: %s", db_plugin.name)
                plugin_instance.on_enable(ctx)
                logger.debug("After on_enable, extension_registry points: %s", extension_registry.list_points())
            except Exception as hook_exc:
                logger.warning("on_enable hook error for '%s': %s", db_plugin.name, hook_exc)

            logger.info("Loaded plugin '%s' v%s", db_plugin.name, db_plugin.version)
            # 成功加载后更新状态和 meta（meta 中可能包含新添加的 character_submodules）
            async with AsyncSessionLocal() as db:
                upd = (await db.execute(
                    select(Plugin).where(Plugin.name == db_plugin.name)
                )).scalar_one_or_none()
                if upd:
                    updated = False
                    if upd.status != "enabled":
                        upd.status = "enabled"
                        upd.error_message = None
                        updated = True
                    # 序列化 submodules 并更新 meta
                    new_meta = dict(upd.meta) if upd.meta else {}
                    new_meta.setdefault("esi_scopes", plugin_instance.get_esi_scopes())
                    new_meta.setdefault("sidebar_items", [
                        {"label": s.label, "route": s.route, "icon": s.icon, "order": s.order}
                        for s in plugin_instance.get_sidebar_items()
                    ])
                    new_meta["character_submodules"] = _serialize_character_submodules(plugin_instance, db_plugin.name)
                    new_meta["beat_schedule"] = serialize_plugin_beat_schedule(plugin_instance)
                    upd.meta = new_meta
                    updated = True
                    logger.debug(
                        "Refreshed plugin %s meta: character_submodules=%d",
                        db_plugin.name, len(new_meta["character_submodules"]),
                    )
                    if updated:
                        await db.commit()
                        logger.debug("Updated plugin %s status/meta to 'enabled'", db_plugin.name)
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
