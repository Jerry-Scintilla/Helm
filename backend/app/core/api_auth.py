"""External API token authentication (separate from EVE SSO JWT flow)."""
import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.api_token import APIToken
from app.models.user import User

_api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

_TOKEN_PREFIX = "hlm_"
_TOKEN_RANDOM_BYTES = 36  # 48 URL-safe base64 chars


def generate_api_token() -> tuple[str, str, str]:
    """
    Returns (full_token, token_prefix, token_hash).
    full_token is shown to the user exactly once.
    """
    random_part = secrets.token_urlsafe(_TOKEN_RANDOM_BYTES)
    full_token = f"{_TOKEN_PREFIX}{random_part}"
    token_prefix = full_token[:8]
    token_hash = hashlib.sha256(full_token.encode()).hexdigest()
    return full_token, token_prefix, token_hash


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_api_key_user(
    authorization: str | None = Security(_api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: authenticate via ApiKey header, return the owning User."""
    if not authorization or not authorization.startswith("ApiKey "):
        raise HTTPException(status_code=401, detail="API key required (Authorization: ApiKey hlm_...)")

    raw_token = authorization.removeprefix("ApiKey ").strip()
    if not raw_token.startswith(_TOKEN_PREFIX):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    token_hash = _hash_token(raw_token)
    now = datetime.now(UTC)

    result = await db.execute(
        select(APIToken).where(
            APIToken.token_hash == token_hash,
            APIToken.is_active == True,
        )
    )
    api_token = result.scalar_one_or_none()

    if api_token is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    if api_token.expires_at and api_token.expires_at < now:
        raise HTTPException(status_code=401, detail="API key has expired")

    api_token.last_used_at = now
    await db.commit()

    user_result = await db.execute(select(User).where(User.id == api_token.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")

    return user


def require_api_scope(scope: str):
    """Dependency factory: ensure the API token has a specific scope."""
    async def _check(
        authorization: str | None = Security(_api_key_header),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if not authorization or not authorization.startswith("ApiKey "):
            raise HTTPException(status_code=401, detail="API key required")

        raw_token = authorization.removeprefix("ApiKey ").strip()
        token_hash = _hash_token(raw_token)

        result = await db.execute(
            select(APIToken).where(APIToken.token_hash == token_hash, APIToken.is_active == True)
        )
        api_token = result.scalar_one_or_none()
        if api_token is None:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if scope not in api_token.scopes.split():
            raise HTTPException(status_code=403, detail=f"API key missing scope: {scope}")

    return _check
