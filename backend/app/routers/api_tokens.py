"""User API token management endpoints (JWT-authenticated)."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_auth import generate_api_token
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.api_token import APIToken
from app.models.user import User
from app.schemas.api_token import APITokenCreateRequest, APITokenCreatedResponse, APITokenResponse

router = APIRouter(prefix="/api/v1/user/tokens", tags=["api-tokens"])


@router.get("/", response_model=list[APITokenResponse])
async def list_tokens(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(APIToken)
        .where(APIToken.user_id == current_user.id, APIToken.is_active == True)
        .order_by(APIToken.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=APITokenCreatedResponse)
async def create_token(
    body: APITokenCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    full_token, token_prefix, token_hash = generate_api_token()
    now = datetime.now(UTC)

    api_token = APIToken(
        user_id=current_user.id,
        name=body.name,
        token_prefix=token_prefix,
        token_hash=token_hash,
        scopes=body.scopes,
        expires_at=body.expires_at,
        created_at=now,
        is_active=True,
    )
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)

    return APITokenCreatedResponse(
        id=api_token.id,
        name=api_token.name,
        token_prefix=api_token.token_prefix,
        scopes=api_token.scopes,
        expires_at=api_token.expires_at,
        last_used_at=api_token.last_used_at,
        is_active=api_token.is_active,
        created_at=api_token.created_at,
        token=full_token,
    )


@router.delete("/{token_id}")
async def revoke_token(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(APIToken).where(APIToken.id == token_id, APIToken.user_id == current_user.id)
    )
    api_token = result.scalar_one_or_none()
    if api_token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    api_token.is_active = False
    await db.commit()
    return {"detail": "Token revoked"}
