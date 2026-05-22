"""
Plugin Manager — orchestrates install / enable / disable / uninstall lifecycle.

The FastAPI app reference is set once by loader.py on startup via set_app().
All public async functions are safe to call from BackgroundTasks (they create
their own DB sessions via AsyncSessionLocal).
"""
import asyncio
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
from app.plugins.base import HelmPlugin, PluginContext, CharacterSubmodule
from app.plugins.events import publish_event
from app.plugins.installer import (
    discover_entry_point,
    load_plugin_class,
    pip_install,
    pip_uninstall,
    run_plugin_downgrade,
    run_plugin_migrations,
)
from app.plugins.registry import HELM_SDK_VERSION, extension_registry, registry
from app.tasks.plugin_schedules import (
    remove_plugin_schedules,
    serialize_plugin_beat_schedule,
    sync_plugin_schedules,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_app: "FastAPI | None" = None

_RESERVED_CHARACTER_SLUGS = {"overview", "wallet", "skills", "assets", "mail", "notifications"}


def _serialize_character_submodules(plugin_instance: HelmPlugin, plugin_name: str) -> list[dict]:
    raw = plugin_instance.get_character_submodules()
    logger.debug(
        "[plugin:%s] get_character_submodules() returned %d items: %s",
        plugin_name, len(raw),
        [{"slug": m.slug, "label": m.label} for m in raw],
    )
    result = []
    for m in raw:
        if m.slug in _RESERVED_CHARACTER_SLUGS:
            logger.warning("Plugin '%s' declares reserved character slug '%s', skipped", plugin_name, m.slug)
            continue
        result.append({
            "slug": m.slug,
            "label": m.label,
            "icon": m.icon,
            "order": m.order,
            "iframe_url_template": m.iframe_url_template,
        })
    return result


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
    module_paths = list(plugin.get_tasks())
    for module_path in module_paths:
        try:
            importlib.import_module(module_path)
            logger.info("Registered Celery tasks from %s", module_path)
        except Exception as exc:
            logger.warning("Failed to import task module %s: %s", module_path, exc)

    # The import above only registers the tasks in *this* (FastAPI) process.
    # Running Celery workers are separate processes that imported plugin task
    # modules at worker_init and won't see these new ones — dispatching them
    # would raise "Received unregistered task". Broadcast a control command so
    # any live workers import the modules and rebuild their strategy map.
    if not module_paths:
        return
    try:
        from app.tasks.celery_app import celery_app
        celery_app.control.broadcast(
            "import_plugin_tasks",
            arguments={"module_paths": module_paths},
        )
        logger.info("Broadcast import_plugin_tasks to workers: %s", module_paths)
    except Exception as exc:
        logger.warning("Failed to broadcast import_plugin_tasks for '%s': %s", plugin.name, exc)


# ── Plugin Beat schedules ───────────────────────────────────────────────────────

async def _publish_plugin_schedules(plugin: HelmPlugin) -> None:
    """Push a plugin's declared Beat schedule to Redis so the running Beat
    process hot-loads its periodic tasks (see app.tasks.helm_scheduler)."""
    entries = serialize_plugin_beat_schedule(plugin)
    try:
        await sync_plugin_schedules(entries, plugin.name)
        if entries:
            logger.info("Published %d Beat schedule entries for '%s'", len(entries), plugin.name)
    except Exception as exc:
        logger.warning("Failed to publish Beat schedules for '%s': %s", plugin.name, exc)


async def _withdraw_plugin_schedules(name: str) -> None:
    """Remove a plugin's Beat entries from Redis (Beat drops them next tick)."""
    try:
        await remove_plugin_schedules(name)
    except Exception as exc:
        logger.warning("Failed to withdraw Beat schedules for '%s': %s", name, exc)


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

async def install_plugin(
    package_name: str,
    whl_path: Path | None = None,
    source: str = "pypi",
) -> dict:
    """
    Full installation flow. Designed to run inside a BackgroundTask.
    Creates its own DB session (caller's session is already closed by then).
    """
    install_target = str(whl_path) if whl_path else package_name
    logger.info("[install:%s] ── START install_target=%s source=%s", package_name, install_target, source)

    await publish_event("plugin.installing", {"package_name": package_name})

    # 1. pip install
    # Capture loop here (async context). on_line runs inside asyncio.to_thread
    # where get_running_loop() raises RuntimeError, so use run_coroutine_threadsafe.
    _loop = asyncio.get_running_loop()
    log_lines: list[str] = []

    def on_line(line: str) -> None:
        log_lines.append(line)
        logger.debug("[install:%s] pip | %s", package_name, line)
        asyncio.run_coroutine_threadsafe(
            publish_event("plugin.install.log", {"line": line}),
            _loop,
        )

    logger.info("[install:%s] step 1/11 — pip install", package_name)
    # whl_path installs are always local file, source flag applies only to name installs
    pip_source = "pypi" if whl_path else source
    ok, output = await pip_install(install_target, on_line=on_line, source=pip_source)
    if not ok:
        logger.error("[install:%s] pip install FAILED:\n%s", package_name, output)
        await publish_event("plugin.install.failed", {"package_name": package_name, "error": output})
        return {"status": "failed", "error": output}
    logger.info("[install:%s] step 1/11 — pip install OK (%d lines)", package_name, len(log_lines))

    # 2. Discover entry point
    logger.info("[install:%s] step 2/11 — discover entry point", package_name)
    result = discover_entry_point(package_name)
    if result is None:
        err = f"No helm.plugins entry point found for package '{package_name}'"
        logger.error("[install:%s] %s", package_name, err)
        await publish_event("plugin.install.failed", {"package_name": package_name, "error": err})
        return {"status": "failed", "error": err}
    entry_point_str, plugin_dir = result
    logger.info("[install:%s] step 2/11 — entry_point=%s  plugin_dir=%s", package_name, entry_point_str, plugin_dir)

    # 3. Load and validate plugin class
    logger.info("[install:%s] step 3/11 — load & validate plugin class", package_name)
    try:
        plugin_class = load_plugin_class(entry_point_str)
        _validate_plugin(plugin_class)
    except Exception as exc:
        err = str(exc)
        logger.error("[install:%s] load/validate FAILED: %s", package_name, err, exc_info=True)
        await publish_event("plugin.install.failed", {"package_name": package_name, "error": err})
        return {"status": "failed", "error": err}
    logger.info(
        "[install:%s] step 3/11 — class=%s  version=%s  sdk_req=%s",
        package_name, plugin_class.__name__, plugin_class.version, plugin_class.helm_sdk_version,
    )

    # 4. Run plugin alembic migrations via main context (in-process)
    logger.info("[install:%s] step 4/11 — alembic migrations", package_name)
    mig_ok, mig_out = await run_plugin_migrations(
        plugin_class.name,
        plugin_dir,
        on_line=lambda line: logger.info("[install:%s] alembic | %s", package_name, line),
    )
    if mig_out.strip() == "no migrations":
        logger.info("[install:%s] step 4/11 — no migrations directory, skipped", package_name)
    elif mig_ok:
        logger.info("[install:%s] step 4/11 — migrations OK:\n%s", package_name, mig_out)
    else:
        # Migration failure leaves the DB in an inconsistent state. We must abort
        # the install — otherwise we'd register a plugin whose tables don't exist,
        # mount its router, and then watch every request 500 at query time.
        err = f"plugin migration failed:\n{mig_out}"
        logger.error("[install:%s] step 4/11 — migrations FAILED, rolling back:\n%s", package_name, mig_out)
        # Best-effort: uninstall the wheel we just installed so the user can retry
        # cleanly after fixing the underlying issue.
        try:
            await pip_uninstall(package_name)
        except Exception as exc:
            logger.warning("[install:%s] rollback pip uninstall errored (non-blocking): %s", package_name, exc)
        await publish_event("plugin.install.failed", {"package_name": package_name, "error": err})
        return {"status": "failed", "error": err}

    # 5. (schema-driven frontend — no JS bundle needed)
    logger.info("[install:%s] step 5/11 — skipped (schema-driven frontend, no bundle)", package_name)
    frontend_bundle_url: str | None = None

    # 6. Instantiate plugin
    logger.info("[install:%s] step 6/11 — instantiate plugin", package_name)
    plugin_instance = plugin_class()

    # 7. Write/update DB record
    logger.info("[install:%s] step 7/11 — write DB record", package_name)
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
            "character_submodules": _serialize_character_submodules(plugin_instance, plugin_class.name),
            "beat_schedule": serialize_plugin_beat_schedule(plugin_instance),
        }
        logger.debug(
            "[install:%s] meta snapshot — esi_scopes=%s  sidebar_items=%d  character_submodules=%d",
            package_name,
            meta_snapshot["esi_scopes"],
            len(meta_snapshot["sidebar_items"]),
            len(meta_snapshot["character_submodules"]),
        )

        if existing is None:
            logger.info("[install:%s] step 7/11 — inserting new Plugin row", package_name)
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
            logger.info("[install:%s] step 7/11 — updating existing Plugin row (id=%s)", package_name, existing.id)
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
        logger.info("[install:%s] step 8/11 — seed permissions", package_name)
        perms = plugin_instance.get_permissions()
        logger.debug("[install:%s] permissions to seed: %s", package_name, [p.name for p in perms])
        await _seed_plugin_permissions(plugin_instance, db)
        await db.commit()
        logger.info("[install:%s] step 8/11 — DB commit OK", package_name)

    # 9. Register in runtime registry and mount router
    # If the plugin was already loaded (reinstall without prior uninstall), remove
    # the old routes first so the new router doesn't get shadowed by stale entries.
    logger.info("[install:%s] step 9/11 — register runtime registry + mount router", package_name)
    if registry.is_loaded(plugin_class.name):
        _unmount_router(plugin_class.name)
        registry.unregister(plugin_class.name)
    registry.register(plugin_instance)
    _mount_router(plugin_instance)
    _register_celery_tasks(plugin_instance)
    await _publish_plugin_schedules(plugin_instance)

    # 10. (schema-driven frontend — no static file mount needed)
    logger.info("[install:%s] step 10/11 — skipped (schema-driven frontend)", package_name)

    # 11. Lifecycle hooks
    logger.info("[install:%s] step 11/11 — lifecycle hooks on_install + on_enable", package_name)
    ctx = _make_context()
    try:
        plugin_instance.on_install(ctx)
        plugin_instance.on_enable(ctx)
    except Exception as exc:
        logger.warning("[install:%s] step 11/11 — lifecycle hook error: %s", package_name, exc, exc_info=True)

    logger.info("[install:%s] ── DONE name=%s version=%s", package_name, plugin_class.name, plugin_class.version)
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
        db_plugin.meta = {
            "esi_scopes": plugin_instance.get_esi_scopes(),
            "sidebar_items": [
                {"label": s.label, "route": s.route, "icon": s.icon, "order": s.order}
                for s in plugin_instance.get_sidebar_items()
            ],
            "character_submodules": _serialize_character_submodules(plugin_instance, name),
            "beat_schedule": serialize_plugin_beat_schedule(plugin_instance),
        }
        await db.commit()

    registry.register(plugin_instance)
    _mount_router(plugin_instance)
    _register_celery_tasks(plugin_instance)
    await _publish_plugin_schedules(plugin_instance)

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
    await _withdraw_plugin_schedules(name)

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

async def uninstall_plugin(name: str) -> None:
    # Disable first (handles hooks + extension registry + router unmount)
    if registry.is_loaded(name):
        await disable_plugin(name)

    # Snapshot what we need from the DB, then close the session immediately.
    # The migration subprocess and pip uninstall can take minutes — holding a
    # DB connection open for that long exhausts the pool and blocks all other
    # requests that need a DB connection.
    async with AsyncSessionLocal() as db:
        db_plugin = (await db.execute(
            select(Plugin).where(Plugin.name == name)
        )).scalar_one_or_none()
        if db_plugin is None:
            return
        package_name = db_plugin.package_name
        entry_point = db_plugin.entry_point

    # 1. on_uninstall hook — must run while package is still importable
    try:
        plugin_class = load_plugin_class(entry_point)
        plugin_class().on_uninstall(_make_context())
    except Exception as exc:
        logger.warning("on_uninstall hook error for '%s': %s", name, exc)

    # 2. Downgrade migrations — must run while package is still importable
    try:
        ep_result = discover_entry_point(package_name)
        if ep_result is not None:
            _ep_str, plugin_dir = ep_result
            mig_ok, mig_out = await run_plugin_downgrade(name, plugin_dir)
            if not mig_ok:
                logger.warning("[uninstall:%s] downgrade failed (non-blocking): %s", name, mig_out)
    except Exception as exc:
        logger.warning("[uninstall:%s] downgrade error (non-blocking): %s", name, exc)

    # 3. pip uninstall
    ok, out = await pip_uninstall(package_name)
    if not ok:
        logger.warning("pip uninstall failed for '%s': %s", name, out)

    # 4. Delete DB record in its own short-lived session
    async with AsyncSessionLocal() as db:
        db_plugin = (await db.execute(
            select(Plugin).where(Plugin.name == name)
        )).scalar_one_or_none()
        if db_plugin is not None:
            await db.delete(db_plugin)
            await db.commit()
            logger.info("Deleted plugin record '%s' from database", name)

    # Belt-and-suspenders: ensure Beat entries are gone even if the plugin was
    # not loaded (so disable_plugin's withdraw never ran).
    await _withdraw_plugin_schedules(name)

    await publish_event("plugin.uninstalled", {"name": name})
