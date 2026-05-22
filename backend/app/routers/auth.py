import asyncio
import json
import secrets
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.bucket import assign_to_bucket
from app.core.permissions import assign_player_role, get_current_user
from app.core.redis import get_pool
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.esi import oauth as eve_oauth
from app.models.character import Character
from app.models.plugin import Plugin
from app.models.user import RefreshToken, User
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

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


async def _dispatch_initial_sync_async(character_db_id: int) -> None:
    await asyncio.to_thread(_dispatch_initial_sync, character_db_id)


def _redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


async def _collect_plugin_scopes() -> list[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Plugin).where(Plugin.is_enabled == True)
        )
        scopes: list[str] = []
        for plugin in result.scalars().all():
            scopes.extend((plugin.meta or {}).get("esi_scopes", []))
        return scopes


@router.get("/eve/login")
async def eve_login():
    """Redirect to EVE SSO login page."""
    state = secrets.token_urlsafe(16)
    plugin_scopes = await _collect_plugin_scopes()
    login_url, verifier = eve_oauth.get_login_url(state, extra_scopes=plugin_scopes or None)
    state_data = json.dumps({"type": "login", "verifier": verifier})
    async with _redis() as r:
        await r.set(f"helm:oauth:state:{state}", state_data, ex=_OAUTH_STATE_TTL)
    return RedirectResponse(login_url)


@router.get("/eve/bind")
async def eve_bind(current_user: User = Depends(get_current_user)):
    """Return an EVE SSO URL for binding an additional character to the current account."""
    state = secrets.token_urlsafe(16)
    plugin_scopes = await _collect_plugin_scopes()
    login_url, verifier = eve_oauth.get_login_url(state, extra_scopes=plugin_scopes or None)
    state_data = json.dumps({"type": "bind", "user_id": current_user.id, "verifier": verifier})
    async with _redis() as r:
        await r.set(f"helm:oauth:state:{state}", state_data, ex=_OAUTH_STATE_TTL)
    return {"redirect_url": login_url}


@router.get("/eve/callback")
async def eve_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle EVE SSO callback. Supports both login and character-bind flows."""
    async with _redis() as r:
        key = f"helm:oauth:state:{state}"
        raw = await r.get(key)
        if raw is not None:
            await r.delete(key)
    if raw is None:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Support old plain-string verifier format for backward compatibility
    raw_str = raw.decode() if isinstance(raw, bytes) else raw
    try:
        state_data = json.loads(raw_str)
        flow_type = state_data.get("type", "login")
        verifier = state_data["verifier"]
    except (json.JSONDecodeError, KeyError):
        flow_type = "login"
        verifier = raw_str

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

    jwt_scopes = char_info.get("scopes", [])
    if isinstance(jwt_scopes, str):
        jwt_scopes = jwt_scopes.split()
    scopes = " ".join(jwt_scopes) if jwt_scopes else token_data.get("scope", "")
    token_expires_at = (
        datetime.now(UTC) + timedelta(seconds=token_data["expires_in"])
        if "expires_in" in token_data else None
    )

    if flow_type == "bind":
        return await _handle_bind(
            db, state_data, character_id, character_name, token_data, scopes, token_expires_at
        )
    else:
        return await _handle_login(
            db, character_id, character_name, token_data, scopes, token_expires_at
        )


async def _handle_bind(db, state_data, character_id, character_name, token_data, scopes, token_expires_at):
    """Bind a new character to an existing user account."""
    user_id = state_data.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=400, detail="Missing user_id in bind state")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Target user not found")

    result = await db.execute(select(Character).where(Character.character_id == character_id))
    character = result.scalar_one_or_none()

    is_new_character = character is None
    if character is None:
        character = Character(
            character_id=character_id,
            user_id=user_id,
            character_name=character_name,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=token_expires_at,
            scopes=scopes,
            is_primary=False,
        )
        db.add(character)
    else:
        # Migrate character from another account — always demote to non-primary
        character.user_id = user_id
        character.is_primary = False
        character.character_name = character_name
        character.access_token = token_data["access_token"]
        character.refresh_token = token_data["refresh_token"]
        character.scopes = scopes
        if token_expires_at is not None:
            character.token_expires_at = token_expires_at

    if is_new_character:
        await db.flush()
        try:
            await assign_to_bucket(character.id, db)
        except Exception:
            pass  # bucket assignment is best-effort; never block login

    await db.commit()
    asyncio.create_task(_dispatch_initial_sync_async(character.id))

    return {"type": "bind", "character_id": character_id, "character_name": character_name}


async def _handle_login(db, character_id, character_name, token_data, scopes, token_expires_at):
    """Login flow: upsert user and character, issue JWT tokens."""
    result = await db.execute(select(User).where(User.username == character_name))
    user = result.scalar_one_or_none()
    is_new_user = user is None
    if is_new_user:
        user = User(username=character_name)
        db.add(user)
        await db.flush()

    result = await db.execute(select(Character).where(Character.character_id == character_id))
    character = result.scalar_one_or_none()

    is_new_character = character is None
    if character is None:
        character = Character(
            character_id=character_id,
            user_id=user.id,
            character_name=character_name,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=token_expires_at,
            scopes=scopes,
            is_primary=True,
        )
        db.add(character)
    else:
        character.access_token = token_data["access_token"]
        character.refresh_token = token_data["refresh_token"]
        character.scopes = scopes
        if token_expires_at is not None:
            character.token_expires_at = token_expires_at

    if is_new_user:
        await assign_player_role(user.id, db)

    # Find the primary character for this user to return in the response
    await db.flush()

    if is_new_character:
        try:
            await assign_to_bucket(character.id, db)
        except Exception:
            pass  # bucket assignment is best-effort; never block login
    primary_result = await db.execute(
        select(Character).where(Character.user_id == user.id, Character.is_primary == True)
    )
    primary = primary_result.scalar_one_or_none()
    if primary is None:
        # Fallback: the character just logged in becomes primary
        character.is_primary = True
        primary = character

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

    asyncio.create_task(_dispatch_initial_sync_async(character.id))

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "character_id": primary.character_id,
        "character_name": primary.character_name,
        "primary_character_id": primary.character_id,
        "primary_character_name": primary.character_name,
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
