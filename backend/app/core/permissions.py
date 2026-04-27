from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.rbac import Permission, RolePermission, UserRole
from app.models.user import User

security = HTTPBearer()

# Built-in permissions seeded on startup
BUILTIN_PERMISSIONS: list[dict] = [
    {"name": "global.superuser", "scope_type": "global", "description": "超级管理员，绕过所有权限检查"},
    {"name": "global.plugin_manage", "scope_type": "global", "description": "管理插件"},
    {"name": "character.view", "scope_type": "character", "description": "查看角色数据"},
    {"name": "corporation.view", "scope_type": "corporation", "description": "查看公司数据"},
    {"name": "alliance.view", "scope_type": "alliance", "description": "查看联盟数据"},
]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def require_permission(permission_name: str):
    """FastAPI dependency factory. Usage: Depends(require_permission('character.view'))"""

    async def checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        # Load user roles → role permissions → permission names
        result = await db.execute(
            select(UserRole)
            .where(UserRole.user_id == current_user.id)
            .options(
                selectinload(UserRole.role).selectinload(
                    RolePermission.permission  # type: ignore[arg-type]
                )
            )
        )
        # Simpler approach: direct join query
        perm_result = await db.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == current_user.id)
        )
        user_perms = {row[0] for row in perm_result.fetchall()}

        if "global.superuser" in user_perms or permission_name in user_perms:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission_name}",
        )

    return checker


async def seed_permissions(db: AsyncSession) -> None:
    """Upsert built-in permissions on startup."""
    for perm_def in BUILTIN_PERMISSIONS:
        result = await db.execute(
            select(Permission).where(Permission.name == perm_def["name"])
        )
        if result.scalar_one_or_none() is None:
            db.add(Permission(**perm_def))
    await db.commit()
