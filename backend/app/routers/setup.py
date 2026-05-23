"""One-time superuser setup endpoint."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.core.security import create_access_token, create_refresh_token
from app.core.setup_token import consume_setup_token
from app.models.character import Character
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import RefreshToken, User

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

_SUPERADMIN_ROLE_NAME = "superadmin"


@router.get("/superuser/{token}")
async def claim_superuser(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Claim the one-time superuser setup link.

    The requesting user must be logged in. The token is consumed on first use.
    Returns a fresh JWT pair so the frontend reflects the new permissions immediately.
    """
    valid = await consume_setup_token(token)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invalid or expired setup token. Use 'helm admin setup-link' to generate a new one.",
        )

    # Find global.superuser permission (seeded on startup, always exists)
    perm_result = await db.execute(
        select(Permission).where(Permission.name == "global.superuser")
    )
    superuser_perm = perm_result.scalar_one_or_none()
    if superuser_perm is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="global.superuser permission not found; ensure the app started correctly.",
        )

    # Find or create the superadmin role
    role_result = await db.execute(
        select(Role).where(Role.name == _SUPERADMIN_ROLE_NAME)
    )
    superadmin_role = role_result.scalar_one_or_none()
    if superadmin_role is None:
        superadmin_role = Role(name=_SUPERADMIN_ROLE_NAME, description="系统超级管理员")
        db.add(superadmin_role)
        await db.flush()

    # Ensure the role has global.superuser permission
    rp_result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == superadmin_role.id,
            RolePermission.permission_id == superuser_perm.id,
        )
    )
    if rp_result.scalar_one_or_none() is None:
        db.add(RolePermission(role_id=superadmin_role.id, permission_id=superuser_perm.id))
        await db.flush()

    # Assign the role to the current user (idempotent)
    ur_result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == current_user.id,
            UserRole.role_id == superadmin_role.id,
        )
    )
    if ur_result.scalar_one_or_none() is None:
        db.add(UserRole(user_id=current_user.id, role_id=superadmin_role.id))

    # Also set the is_superuser flag so it is reflected in future token responses
    current_user.is_superuser = True

    # Issue a fresh JWT pair so the caller can skip re-login
    access_token = create_access_token(current_user.id)
    raw_refresh, hashed_refresh = create_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.jwt_refresh_token_expire)
    db.add(RefreshToken(user_id=current_user.id, token_hash=hashed_refresh, expires_at=expires_at))

    # Resolve primary character for the token payload
    primary_result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id,
            Character.is_primary == True,
        )
    )
    primary = primary_result.scalar_one_or_none()

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "character_id": primary.character_id if primary else None,
        "character_name": primary.character_name if primary else current_user.username,
        "primary_character_id": primary.character_id if primary else None,
        "primary_character_name": primary.character_name if primary else current_user.username,
        "is_superuser": True,
    }
