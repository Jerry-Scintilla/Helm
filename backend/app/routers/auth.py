import secrets
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import assign_player_role
from app.core.redis import get_pool
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.esi import oauth as eve_oauth
from app.models.character import Character
from app.models.user import RefreshToken, User
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_TTL = 600  # 10 minutes


def _dispatch_initial_sync(character_db_id: int) -> None:
    """Fire-and-forget ESI sync tasks for a freshly logged-in character."""
    queue = "characters"
    for task_name in (
        "app.tasks.characters.wallet.update_wallet",
        "app.tasks.characters.skills.update_skills",
        "app.tasks.characters.assets.update_assets",
        "app.tasks.characters.skill_queue.update_skill_queue",
        "app.tasks.characters.notifications.update_notifications",
        "app.tasks.characters.mail.update_mail",
        "app.tasks.characters.wallet_journal.update_wallet_journal",
        "app.tasks.characters.wallet_transactions.update_wallet_transactions",
    ):
        celery_app.send_task(task_name, args=[character_db_id], queue=queue)


def _redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


@router.get("/eve/login")
async def eve_login():
    """Redirect to EVE SSO login page."""
    state = secrets.token_urlsafe(16)
    login_url, verifier = eve_oauth.get_login_url(state)
    async with _redis() as r:
        await r.set(f"helm:oauth:state:{state}", verifier, ex=_OAUTH_STATE_TTL)
    return RedirectResponse(login_url)


@router.get("/eve/callback")
async def eve_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle EVE SSO callback, create/update user, return JWT tokens."""
    async with _redis() as r:
        key = f"helm:oauth:state:{state}"
        verifier = await r.get(key)
        if verifier is not None:
            await r.delete(key)
    if verifier is None:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        token_data = await eve_oauth.exchange_code(code, verifier)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to exchange code with EVE SSO")

    try:
        char_info = await eve_oauth.verify_token(token_data["access_token"])
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to verify EVE token")

    character_id = char_info["character_id"]
    character_name = char_info["character_name"]

    # Upsert User (keyed by character_name as username for now)
    result = await db.execute(select(User).where(User.username == character_name))
    user = result.scalar_one_or_none()
    is_new_user = user is None
    if is_new_user:
        user = User(username=character_name)
        db.add(user)
        await db.flush()

    # Upsert Character
    result = await db.execute(select(Character).where(Character.character_id == character_id))
    character = result.scalar_one_or_none()
    scopes = token_data.get("scope", "")
    if character is None:
        character = Character(
            character_id=character_id,
            user_id=user.id,
            character_name=character_name,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            scopes=scopes,
        )
        db.add(character)
    else:
        character.access_token = token_data["access_token"]
        character.refresh_token = token_data["refresh_token"]
        character.scopes = scopes

    if is_new_user:
        await assign_player_role(user.id, db)

    # Issue Helm JWT tokens
    access_token = create_access_token(user.id)
    raw_refresh, hashed_refresh = create_refresh_token()

    expires_at = datetime.now(UTC) + timedelta(seconds=settings.jwt_refresh_token_expire)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=expires_at,
    )
    db.add(db_refresh)
    await db.commit()

    # Trigger immediate ESI sync for this character
    _dispatch_initial_sync(character.id)

    # Return tokens — in production set as HttpOnly cookies
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "character_id": character_id,
        "character_name": character_name,
        "is_superuser": user.is_superuser,
    }


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/token/refresh")
async def token_refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh_token for a new access_token."""
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    access_token = create_access_token(db_token.user_id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Revoke the refresh token."""
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        await db.commit()
    return {"detail": "Logged out"}
