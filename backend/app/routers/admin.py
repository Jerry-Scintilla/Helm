from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_user, require_permission
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User

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
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        {"id": u.id, "username": u.username, "is_active": u.is_active, "is_superuser": u.is_superuser}
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
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]


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
