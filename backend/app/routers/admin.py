import json
from datetime import UTC, datetime

import redis.asyncio as aioredis
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import get_current_user, require_permission
from app.core.redis import get_pool
from app.models.alliance import Alliance
from app.models.bucket import Bucket, BucketToken
from app.models.character import Character
from app.models.corporation import Corporation
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.schemas.admin import SDEImportRequest, SDEStatusResponse, SDEUploadResponse
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name: str
    description: str = ""


class RoleAssign(BaseModel):
    role_id: int


class PermissionAssign(BaseModel):
    permission_id: int


# ── Users ────────────────────────────────────────────────────────────────────

@router.get("/users/")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(
        select(User).options(
            selectinload(User.user_roles).selectinload(UserRole.role)
        )
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "created_at": u.created_at,
            "roles": [
                {"id": ur.role.id, "name": ur.role.name, "description": ur.role.description}
                for ur in u.user_roles
            ],
        }
        for u in users
    ]


@router.post("/users/{user_id}/roles")
async def assign_role(
    user_id: int,
    body: RoleAssign,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == body.role_id)
    )
    if result.scalar_one_or_none() is None:
        db.add(UserRole(user_id=user_id, role_id=body.role_id))
        await db.commit()
    return {"detail": "Role assigned"}


# ── Roles ────────────────────────────────────────────────────────────────────

@router.get("/roles/")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(
        select(Role).options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
    )
    roles = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "permissions": [
                {"id": rp.permission.id, "name": rp.permission.name, "scope_type": rp.permission.scope_type}
                for rp in r.role_permissions
            ],
        }
        for r in roles
    ]


@router.post("/roles/")
async def create_role(
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    role = Role(name=body.name, description=body.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return {"id": role.id, "name": role.name}


@router.post("/roles/{role_id}/permissions")
async def assign_permission(
    role_id: int,
    body: PermissionAssign,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == body.permission_id,
        )
    )
    if result.scalar_one_or_none() is None:
        db.add(RolePermission(role_id=role_id, permission_id=body.permission_id))
        await db.commit()
    return {"detail": "Permission assigned"}


# ── Permissions list ──────────────────────────────────────────────────────────

@router.get("/permissions/")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(select(Permission))
    perms = result.scalars().all()
    return [{"id": p.id, "name": p.name, "scope_type": p.scope_type} for p in perms]


# ── Delete endpoints ──────────────────────────────────────────────────────────

@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    return {"detail": "User deactivated"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_user_role(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    user_role = result.scalar_one_or_none()
    if user_role is None:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    await db.delete(user_role)
    await db.commit()
    return {"detail": "Role removed"}


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    await db.delete(role)
    await db.commit()
    return {"detail": "Role deleted"}


@router.delete("/roles/{role_id}/permissions/{permission_id}")
async def remove_role_permission(
    role_id: int,
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    rp = result.scalar_one_or_none()
    if rp is None:
        raise HTTPException(status_code=404, detail="Permission assignment not found")
    await db.delete(rp)
    await db.commit()
    return {"detail": "Permission removed"}


# ── Buckets ───────────────────────────────────────────────────────────────────

class BucketCreate(BaseModel):
    name: str
    capacity: int = 100
    description: str = ""


class BucketUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    is_active: bool | None = None
    description: str | None = None


@router.get("/buckets/")
async def list_buckets(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(select(Bucket))
    buckets = list(result.scalars().all())

    r = aioredis.Redis(connection_pool=get_pool())
    try:
        response = []
        for bucket in buckets:
            token_count_result = await db.execute(
                select(func.count()).select_from(BucketToken).where(BucketToken.bucket_id == bucket.id)
            )
            token_count = token_count_result.scalar() or 0

            state_raw = await r.get(f"helm:bucket:{bucket.id}:state")
            state = json.loads(state_raw) if state_raw else {}
            response.append({
                "id": bucket.id,
                "name": bucket.name,
                "capacity": bucket.capacity,
                "is_active": bucket.is_active,
                "description": bucket.description,
                "created_at": bucket.created_at,
                "state": {
                    "token_count": token_count,
                    "health": state.get("health", "unknown"),
                    "last_run_at": state.get("last_run_at"),
                    "active_task_count": state.get("active_task_count", 0),
                },
            })
        return response
    finally:
        await r.aclose()


@router.post("/buckets/")
async def create_bucket(
    body: BucketCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    bucket = Bucket(name=body.name, capacity=body.capacity, description=body.description)
    db.add(bucket)
    await db.commit()
    await db.refresh(bucket)
    return {"id": bucket.id, "name": bucket.name, "capacity": bucket.capacity}


@router.put("/buckets/{bucket_id}")
async def update_bucket(
    bucket_id: int,
    body: BucketUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(select(Bucket).where(Bucket.id == bucket_id))
    bucket = result.scalar_one_or_none()
    if bucket is None:
        raise HTTPException(status_code=404, detail="Bucket not found")

    if body.name is not None:
        bucket.name = body.name
    if body.capacity is not None:
        bucket.capacity = body.capacity
    if body.is_active is not None:
        bucket.is_active = body.is_active
    if body.description is not None:
        bucket.description = body.description

    await db.commit()
    return {"detail": "Bucket updated"}


@router.get("/buckets/{bucket_id}/tokens")
async def get_bucket_tokens(
    bucket_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    result = await db.execute(select(BucketToken).where(BucketToken.bucket_id == bucket_id))
    tokens = result.scalars().all()
    return [
        {
            "character_id": t.character_id,
            "last_refreshed_at": t.last_refreshed_at,
            "refresh_count": t.refresh_count,
            "error_count": t.error_count,
        }
        for t in tokens
    ]


# ── System stats ──────────────────────────────────────────────────────────────

@router.get("/system/stats")
async def system_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    users = (await db.execute(select(func.count()).select_from(User))).scalar()
    chars = (await db.execute(select(func.count()).select_from(Character))).scalar()
    corps = (await db.execute(select(func.count()).select_from(Corporation))).scalar()
    alliances = (await db.execute(select(func.count()).select_from(Alliance))).scalar()
    buckets = (await db.execute(select(func.count()).select_from(Bucket))).scalar()
    bucket_tokens = (await db.execute(select(func.count()).select_from(BucketToken))).scalar()

    return {
        "total_users": users,
        "total_characters": chars,
        "total_corporations": corps,
        "total_alliances": alliances,
        "total_buckets": buckets,
        "total_bucket_tokens": bucket_tokens,
    }


# ── SDE ───────────────────────────────────────────────────────────────────────

@router.post("/sde/import", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sde_import(
    body: SDEImportRequest | None = None,
    _: User = Depends(require_permission("global.superuser")),
):
    url = (body.url or settings.sde_default_jsonl_url) if body else settings.sde_default_jsonl_url
    task = celery_app.send_task("app.tasks.sde.import_sde", args=[url], kwargs={}, queue="high")
    return {"task_id": task.id, "status": "dispatched", "source": "url"}


@router.post("/sde/upload", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sde_upload(
    file: UploadFile = File(...),
    _: User = Depends(require_permission("global.superuser")),
):
    """Accept a user-uploaded eve-online-static-data-latest-jsonl.zip file."""
    import uuid

    upload_dir = Path(settings.sde_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix.lower() if file.filename else ".zip"
    if suffix != ".zip":
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    filename = f"{uuid.uuid4().hex}{suffix}"
    file_path = upload_dir / filename

    content = await file.read()
    if len(content) > 500 * 1024 * 1024:  # 500 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 500 MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    task = celery_app.send_task(
        "app.tasks.sde.import_sde",
        kwargs={"uploaded_file_path": str(file_path)},
        queue="high",
    )
    return {"task_id": task.id, "status": "dispatched", "filename": file.filename}


@router.get("/sde/import/{task_id}")
async def get_sde_import_status(
    task_id: str,
    _: User = Depends(require_permission("global.superuser")),
):
    result = celery_app.AsyncResult(task_id)
    if result.failed():
        return {"task_id": task_id, "status": "failure", "result": None, "error": str(result.result)}
    if result.successful():
        return {"task_id": task_id, "status": "success", "result": result.result, "error": None}
    return {"task_id": task_id, "status": result.state.lower(), "result": None, "error": None}


@router.get("/sde/status")
async def get_sde_status(
    _: User = Depends(require_permission("global.superuser")),
):
    """Return current SDE import status and metadata stored in Redis."""
    r = aioredis.Redis(connection_pool=get_pool())
    try:
        status_val = await r.get("helm:sde:status") or "idle"
        version = await r.get("helm:sde:version")
        release_date = await r.get("helm:sde:release_date")
        row_count_str = await r.get("helm:sde:row_count")
        last_import_at_str = await r.get("helm:sde:last_import_at")
        last_error = await r.get("helm:sde:last_error")
        source_url = await r.get("helm:sde:source_url")

        last_import_at = None
        if last_import_at_str:
            ts = int(last_import_at_str)
            last_import_at = datetime.fromtimestamp(ts, tz=UTC).isoformat()

        return {
            "status": status_val,
            "version": version,
            "release_date": release_date,
            "row_count": int(row_count_str) if row_count_str else None,
            "last_import_at": last_import_at,
            "last_error": last_error or None,
            "source_url": source_url or None,
        }
    finally:
        await r.aclose()
