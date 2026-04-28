"""
Plugin Manager — orchestrates install / enable / disable / uninstall lifecycle.

The FastAPI app reference is set once by loader.py on startup via set_app().
All public async functions are safe to call from BackgroundTasks (they create
their own DB sessions via AsyncSessionLocal).
"""
import importlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.plugin import Plugin
from app.plugins.base import HelmPlugin, PluginContext
from app.plugins.events import publish_event
from app.plugins.installer import (
    discover_entry_point,
    load_plugin_class,
    pip_install,
    pip_uninstall,
    run_plugin_migrations,
)
from app.plugins.registry import HELM_SDK_VERSION, extension_registry, registry

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_app: "FastAPI | None" = None


def set_app(app: "FastAPI") -> None:
    global _app
    _app = app


# ── Router hot-swap ───────────────────────────────────────────────────────────

def _mount_router(plugin: HelmPlugin) -> None:
    if _app is None:
        return
    router = plugin.get_router()
    if router is None:
        return
    prefix = f"/api/v1/plugins/{plugin.name}"
    _app.include_router(router, prefix=prefix)
    _app.openapi_schema = None
    registry.register(plugin, route_prefix=prefix)
    logger.info("Mounted router for plugin '%s' at %s", plugin.name, prefix)


def _unmount_router(name: str) -> None:
    """
    Remove routes belonging to this plugin from app.router.routes.
    This is a best-effort Starlette internal API — new requests will see the
    change immediately; in-flight requests are unaffected.
    """
    if _app is None:
        return
    prefix = registry.get_route_prefix(name)
    if not prefix:
        return
    _app.router.routes = [
        r for r in _app.router.routes
        if not getattr(r, "path", "").startswith(prefix)
    ]
    _app.openapi_schema = None
    logger.info("Unmounted router for plugin '%s'", name)


# ── Celery task registration ──────────────────────────────────────────────────

def _register_celery_tasks(plugin: HelmPlugin) -> None:
    for module_path in plugin.get_tasks():
        try:
            importlib.import_module(module_path)
            logger.info("Registered Celery tasks from %s", module_path)
        except Exception as exc:
            logger.warning("Failed to import task module %s: %s", module_path, exc)


# ── Permission seeding ────────────────────────────────────────────────────────

async def _seed_plugin_permissions(plugin: HelmPlugin, db) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.models.rbac import Permission
    for perm_def in plugin.get_permissions():
        result = await db.execute(
            select(Permission).where(Permission.name == perm_def.name)
        )
        if result.scalar_one_or_none() is None:
            db.add(Permission(
                name=perm_def.name,
                scope_type=perm_def.scope_type,
                description=perm_def.description,
            ))
    await db.flush()


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_plugin(plugin_class) -> None:
    if not (isinstance(plugin_class, type) and issubclass(plugin_class, HelmPlugin)):
        raise ValueError(f"{plugin_class} is not a subclass of HelmPlugin")
    specifier = SpecifierSet(plugin_class.helm_sdk_version)
    if Version(HELM_SDK_VERSION) not in specifier:
        raise ValueError(
            f"Plugin requires helm_sdk_version '{plugin_class.helm_sdk_version}', "
            f"but server SDK version is '{HELM_SDK_VERSION}'"
        )


# ── Plugin context factory ────────────────────────────────────────────────────

def _make_context() -> PluginContext:
    return PluginContext(db_session_factory=AsyncSessionLocal)


# ── Install ───────────────────────────────────────────────────────────────────

async def install_plugin(package_name: str, whl_path: Path | None = None) -> dict:
    """
    Full installation flow. Designed to run inside a BackgroundTask.
    Creates its own DB session (caller's session is already closed by then).
    """
    install_target = str(whl_path) if whl_path else package_name

    await publish_event("plugin.installing", {"package_name": package_name})

    # 1. pip install
    async def _on_line(line: str) -> None:
        await publish_event("plugin.install.log", {"line": line})

    # BackgroundTask is sync-called, but install_plugin is async — wrap callback
    log_lines: list[str] = []

    def on_line(line: str) -> None:
        log_lines.append(line)
        # Fire-and-forget publish (we're inside an async context)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(publish_event("plugin.install.log", {"line": line}))
        except RuntimeError:
            pass

    ok, output = await pip_install(install_target, on_line=on_line)
    if not ok:
        await publish_event("plugin.install.failed", {"package_name": package_name, "error": output})
        return {"status": "failed", "error": output}

    # 2. Discover entry point
    result = discover_entry_point(package_name)
    if result is None:
        err = f"No helm.plugins entry point found for package '{package_name}'"
        await publish_event("plugin.install.failed", {"package_name": package_name, "error": err})
        return {"status": "failed", "error": err}
    entry_point_str, plugin_dir = result

    # 3. Load and validate plugin class
    try:
        plugin_class = load_plugin_class(entry_point_str)
        _validate_plugin(plugin_class)
    except Exception as exc:
        err = str(exc)
        await publish_event("plugin.install.failed", {"package_name": package_name, "error": err})
        return {"status": "failed", "error": err}

    # 4. Run plugin-own alembic migrations
    mig_ok, mig_out = await run_plugin_migrations(plugin_dir)
    if not mig_ok:
        logger.warning("Plugin migration warning for '%s': %s", package_name, mig_out)

    # 5. Detect frontend bundle
    frontend_dist = plugin_dir / "frontend" / "dist"
    frontend_bundle_url: str | None = None
    if frontend_dist.exists():
        frontend_bundle_url = f"/static/plugins/{plugin_class.name}"

    # 6. Instantiate plugin
    plugin_instance = plugin_class()

    # 7. Write/update DB record
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(Plugin).where(Plugin.name == plugin_class.name)
        )).scalar_one_or_none()

        meta_snapshot = {
            "esi_scopes": plugin_instance.get_esi_scopes(),
            "sidebar_items": [
                {"label": s.label, "route": s.route, "icon": s.icon, "order": s.order}
                for s in plugin_instance.get_sidebar_items()
            ],
            "widgets": [
                {"component": w.component, "title": w.title, "order": w.order}
                for w in plugin_instance.get_dashboard_widgets()
            ],
        }

        if existing is None:
            db_plugin = Plugin(
                name=plugin_class.name,
                package_name=package_name,
                entry_point=entry_point_str,
                version=plugin_class.version,
                author=plugin_class.author,
                description=plugin_class.description,
                helm_sdk_version=plugin_class.helm_sdk_version,
                is_enabled=True,
                status="enabled",
                meta=meta_snapshot,
                frontend_bundle_url=frontend_bundle_url,
            )
            db.add(db_plugin)
        else:
            existing.package_name = package_name
            existing.entry_point = entry_point_str
            existing.version = plugin_class.version
            existing.author = plugin_class.author
            existing.description = plugin_class.description
            existing.helm_sdk_version = plugin_class.helm_sdk_version
            existing.is_enabled = True
            existing.status = "enabled"
            existing.error_message = None
            existing.meta = meta_snapshot
            existing.frontend_bundle_url = frontend_bundle_url
            existing.updated_at = datetime.now(UTC)

        # 8. Seed permissions
        await _seed_plugin_permissions(plugin_instance, db)
        await db.commit()

    # 9. Register in runtime registry and mount router
    registry.register(plugin_instance)
    _mount_router(plugin_instance)
    _register_celery_tasks(plugin_instance)

    # 10. Mount frontend static files
    if frontend_bundle_url and _app is not None:
        from fastapi.staticfiles import StaticFiles
        _app.mount(
            frontend_bundle_url,
            StaticFiles(directory=str(frontend_dist)),
            name=f"plugin-{plugin_class.name}",
        )

    # 11. Lifecycle hooks
    ctx = _make_context()
    try:
        plugin_instance.on_install(ctx)
        plugin_instance.on_enable(ctx)
    except Exception as exc:
        logger.warning("Plugin lifecycle hook error for '%s': %s", plugin_class.name, exc)

    await publish_event("plugin.installed", {
        "name": plugin_class.name,
        "version": plugin_class.version,
        "package_name": package_name,
    })
    return {"status": "installed", "name": plugin_class.name}


# ── Enable ────────────────────────────────────────────────────────────────────

async def enable_plugin(name: str) -> None:
    async with AsyncSessionLocal() as db:
        db_plugin = (await db.execute(
            select(Plugin).where(Plugin.name == name)
        )).scalar_one_or_none()
        if db_plugin is None:
            raise ValueError(f"Plugin '{name}' not found in database")
        if db_plugin.status == "uninstalled":
            raise ValueError(f"Plugin '{name}' is uninstalled; reinstall first")

        try:
            plugin_class = load_plugin_class(db_plugin.entry_point)
            _validate_plugin(plugin_class)
            plugin_instance = plugin_class()
        except Exception as exc:
            db_plugin.status = "error"
            db_plugin.error_message = str(exc)
            await db.commit()
            raise

        db_plugin.is_enabled = True
        db_plugin.status = "enabled"
        db_plugin.error_message = None
        db_plugin.updated_at = datetime.now(UTC)
        await db.commit()

    registry.register(plugin_instance)
    _mount_router(plugin_instance)
    _register_celery_tasks(plugin_instance)

    ctx = _make_context()
    try:
        plugin_instance.on_enable(ctx)
    except Exception as exc:
        logger.warning("on_enable hook error for '%s': %s", name, exc)

    await publish_event("plugin.enabled", {"name": name})


# ── Disable ───────────────────────────────────────────────────────────────────

async def disable_plugin(name: str) -> None:
    plugin = registry.get(name)
    if plugin is not None:
        ctx = _make_context()
        try:
            plugin.on_disable(ctx)
        except Exception as exc:
            logger.warning("on_disable hook error for '%s': %s", name, exc)

    extension_registry.unregister_plugin(name)
    _unmount_router(name)
    registry.unregister(name)

    async with AsyncSessionLocal() as db:
        db_plugin = (await db.execute(
            select(Plugin).where(Plugin.name == name)
        )).scalar_one_or_none()
        if db_plugin:
            db_plugin.is_enabled = False
            db_plugin.status = "disabled"
            db_plugin.updated_at = datetime.now(UTC)
            await db.commit()

    await publish_event("plugin.disabled", {"name": name})


# ── Uninstall ─────────────────────────────────────────────────────────────────

async def uninstall_plugin(name: str, pip_remove: bool = False) -> None:
    # Disable first (handles hooks + extension registry + router unmount)
    if registry.is_loaded(name):
        await disable_plugin(name)

    if pip_remove:
        async with AsyncSessionLocal() as db:
            db_plugin = (await db.execute(
                select(Plugin).where(Plugin.name == name)
            )).scalar_one_or_none()
            if db_plugin:
                ok, out = await pip_uninstall(db_plugin.package_name)
                if not ok:
                    logger.warning("pip uninstall failed for '%s': %s", name, out)

    async with AsyncSessionLocal() as db:
        db_plugin = (await db.execute(
            select(Plugin).where(Plugin.name == name)
        )).scalar_one_or_none()
        if db_plugin:
            plugin_class = None
            try:
                plugin_class = load_plugin_class(db_plugin.entry_point)
            except Exception:
                pass
            if plugin_class:
                ctx = _make_context()
                try:
                    plugin_class().on_uninstall(ctx)
                except Exception as exc:
                    logger.warning("on_uninstall hook error for '%s': %s", name, exc)
            db_plugin.is_enabled = False
            db_plugin.status = "uninstalled"
            db_plugin.updated_at = datetime.now(UTC)
            await db.commit()

    await publish_event("plugin.uninstalled", {"name": name})
