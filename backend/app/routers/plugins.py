import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from jose import JWTError
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.permissions import get_current_user, require_permission
from app.core.security import decode_access_token
from app.models.plugin import Plugin
from app.models.user import User
from app.plugins import events
from app.plugins.base import HelmPlugin
from app.plugins.manager import disable_plugin, enable_plugin, install_plugin, uninstall_plugin
from app.plugins.registry import extension_registry, registry
from app.schemas.plugin import InstallRequest, InstallResponse, PluginInfo, PluginStatusResponse


def _compute_frontend_url(plugin: HelmPlugin, name: str) -> str | None:
    """Compute the iframe src URL for a plugin's frontend.

    In development, returns the plugin's dev server URL if declared.
    Otherwise, returns the /plugin-ui/{name}/index.html path when a
    compiled static dir exists.
    """
    if settings.app_env == "development":
        dev_url = plugin.get_frontend_dev_url()
        if dev_url:
            return dev_url
    static_dir = plugin.get_static_dir()
    if static_dir and (static_dir / "index.html").exists():
        return f"/plugin-ui/{name}/index.html"
    return None

# Admin-only router (requires global.plugin_manage)
router = APIRouter(prefix="/api/v1/admin/plugins", tags=["plugins-admin"])

# Public router (enabled plugin manifest for frontend dynamic routing)
public_router = APIRouter(prefix="/api/v1/plugins", tags=["plugins-public"])


# ── SSE auth helper (EventSource cannot send custom headers) ──────────────────

async def _verify_sse_token(token: str) -> User:
    """Validate JWT from query parameter and return the authenticated user."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exc

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user


async def _verify_sse_permission(token: str) -> User:
    user = await _verify_sse_token(token)
    if not user.is_superuser:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select as sa_select
            from app.models.rbac import Permission, RolePermission, UserRole
            perm_result = await db.execute(
                sa_select(Permission.name)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(UserRole, UserRole.role_id == RolePermission.role_id)
                .where(UserRole.user_id == user.id)
            )
            perms = {row[0] for row in perm_result.fetchall()}
        if "global.superuser" not in perms and "global.plugin_manage" not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission required: global.plugin_manage")
    return user


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/", response_model=list[PluginInfo])
async def list_plugins(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.plugin_manage")),
):
    result = await db.execute(select(Plugin).order_by(Plugin.installed_at))
    plugins = result.scalars().all()
    infos = []
    for p in plugins:
        info = PluginInfo.model_validate(p)
        instance = registry.get(p.name)
        if instance:
            info = info.model_copy(update={"frontend_url": _compute_frontend_url(instance, p.name)})
        infos.append(info)
    return infos


@router.get("/events")
async def plugin_events(token: Annotated[str, Query()]):
    """SSE stream of plugin lifecycle events. Auth via ?token=<jwt>."""
    await _verify_sse_permission(token)
    return StreamingResponse(
        events.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/install", response_model=InstallResponse)
async def install_by_name(
    req: InstallRequest,
    background_tasks: BackgroundTasks,
    _: User = Depends(require_permission("global.plugin_manage")),
):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(install_plugin, req.package_name)
    return InstallResponse(task_id=task_id, status="installing")


@router.post("/install/upload", response_model=InstallResponse)
async def install_by_upload(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    _: User = Depends(require_permission("global.plugin_manage")),
):
    if not file.filename or not file.filename.endswith(".whl"):
        raise HTTPException(status_code=400, detail="Only .whl files are accepted")

    upload_dir = Path(settings.sde_upload_dir).parent / "plugins"
    upload_dir.mkdir(parents=True, exist_ok=True)
    whl_path = upload_dir / file.filename
    content = await file.read()
    whl_path.write_bytes(content)

    package_name = file.filename.split("-")[0].replace("_", "-")
    task_id = str(uuid.uuid4())
    background_tasks.add_task(install_plugin, package_name, whl_path)
    return InstallResponse(task_id=task_id, status="installing")


@router.post("/{name}/enable", status_code=204)
async def enable(
    name: str,
    _: User = Depends(require_permission("global.plugin_manage")),
):
    try:
        await enable_plugin(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{name}/disable", status_code=204)
async def disable(
    name: str,
    _: User = Depends(require_permission("global.plugin_manage")),
):
    await disable_plugin(name)


@router.delete("/{name}", status_code=204)
async def uninstall(
    name: str,
    pip_remove: bool = False,
    _: User = Depends(require_permission("global.plugin_manage")),
):
    await uninstall_plugin(name, pip_remove=pip_remove)


@router.get("/{name}/status", response_model=PluginStatusResponse)
async def plugin_status(
    name: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.plugin_manage")),
):
    db_plugin = (await db.execute(
        select(Plugin).where(Plugin.name == name)
    )).scalar_one_or_none()
    if db_plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    prefix = registry.get_route_prefix(name)
    return PluginStatusResponse(
        name=name,
        status=db_plugin.status,
        is_enabled=db_plugin.is_enabled,
        is_loaded=registry.is_loaded(name),
        router_mounted=prefix is not None,
        error_message=db_plugin.error_message,
    )


# ── Public endpoints ──────────────────────────────────────────────────────────

@public_router.get("/", response_model=list[PluginInfo])
async def list_enabled_plugins(db: AsyncSession = Depends(get_db)):
    """Public endpoint: returns enabled plugin manifest for frontend dynamic routing."""
    result = await db.execute(
        select(Plugin).where(Plugin.is_enabled == True, Plugin.status == "enabled")
    )
    plugins = result.scalars().all()
    infos = []
    for p in plugins:
        info = PluginInfo.model_validate(p)
        instance = registry.get(p.name)
        if instance:
            info = info.model_copy(update={"frontend_url": _compute_frontend_url(instance, p.name)})
        infos.append(info)
    return infos
