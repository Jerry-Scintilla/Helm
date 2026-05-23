"""One-time superuser setup token stored in Redis."""
import secrets

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_pool

SETUP_TOKEN_KEY = "helm:setup:superuser_token"
SETUP_TOKEN_TTL = 86400  # 24 hours


async def generate_setup_token() -> str:
    token = secrets.token_urlsafe(32)
    r = aioredis.Redis(connection_pool=get_pool())
    try:
        await r.set(SETUP_TOKEN_KEY, token, ex=SETUP_TOKEN_TTL)
    finally:
        await r.aclose()
    return token


async def consume_setup_token(token: str) -> bool:
    """Atomically verify and delete the token. Returns True only if the token matched."""
    r = aioredis.Redis(connection_pool=get_pool())
    try:
        stored = await r.get(SETUP_TOKEN_KEY)
        if stored is None or stored != token:
            return False
        await r.delete(SETUP_TOKEN_KEY)
        return True
    finally:
        await r.aclose()


async def has_any_superuser(db: AsyncSession) -> bool:
    from app.models.rbac import Permission, RolePermission, UserRole
    from app.models.user import User

    result = await db.execute(select(User).where(User.is_superuser == True))
    if result.scalar_one_or_none() is not None:
        return True

    result = await db.execute(
        select(UserRole.user_id)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(Permission.name == "global.superuser")
    )
    return result.first() is not None
