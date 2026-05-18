from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User

security = HTTPBearer()

# Built-in permissions seeded on startup
BUILTIN_PERMISSIONS: list[dict] = [
    {"name": "global.superuser", "scope_type": "global", "description": "超级管理员，绕过所有权限检查"},
    {"name": "global.plugin_manage", "scope_type": "global", "description": "管理插件"},
    {"name": "character.view", "scope_type": "character", "description": "查看角色数据"},
    {"name": "corporation.view", "scope_type": "corporation", "description": "查看公司数据"},
    {"name": "corporation.manage_members", "scope_type": "corporation", "description": "管理公司成员"},
    {"name": "alliance.view", "scope_type": "alliance", "description": "查看联盟数据"},
    {"name": "bucket.manage", "scope_type": "global", "description": "管理 Bucket 调度"},
    {"name": "api.external_access", "scope_type": "global", "description": "外部 API Token 访问"},
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


PLAYER_ROLE_NAME = "player"
PLAYER_ROLE_PERMISSIONS = ["character.view", "corporation.view", "alliance.view"]


async def seed_permissions(db: AsyncSession) -> None:
    """Upsert built-in permissions and the default player role on startup."""
    for perm_def in BUILTIN_PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.name == perm_def["name"]))
        if result.scalar_one_or_none() is None:
            db.add(Permission(**perm_def))
    await db.flush()

    # Ensure the built-in player role exists
    result = await db.execute(select(Role).where(Role.name == PLAYER_ROLE_NAME))
    player_role = result.scalar_one_or_none()
    if player_role is None:
        player_role = Role(name=PLAYER_ROLE_NAME, description="所有通过EVE SSO注册的用户默认角色")
        db.add(player_role)
        await db.flush()

    # Ensure player role has the required permissions
    for perm_name in PLAYER_ROLE_PERMISSIONS:
        perm_result = await db.execute(select(Permission).where(Permission.name == perm_name))
        perm = perm_result.scalar_one_or_none()
        if perm is None:
            continue
        existing = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == player_role.id,
                RolePermission.permission_id == perm.id,
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(RolePermission(role_id=player_role.id, permission_id=perm.id))

    # Backfill: assign player role to any existing users who don't have it yet
    users_without_role = await db.execute(
        select(User.id).where(
            ~User.id.in_(
                select(UserRole.user_id).where(UserRole.role_id == player_role.id)
            )
        )
    )
    for (uid,) in users_without_role.fetchall():
        db.add(UserRole(user_id=uid, role_id=player_role.id))

    await db.commit()


async def assign_player_role(user_id: int, db: AsyncSession) -> None:
    """Assign the default player role to a newly registered user."""
    result = await db.execute(select(Role).where(Role.name == PLAYER_ROLE_NAME))
    player_role = result.scalar_one_or_none()
    if player_role is None:
        return
    existing = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == player_role.id)
    )
    if existing.scalar_one_or_none() is None:
        db.add(UserRole(user_id=user_id, role_id=player_role.id))
