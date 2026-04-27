from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.alliance import Alliance, AllianceCorporation
from app.models.user import User

router = APIRouter(prefix="/api/v1/alliances", tags=["alliances"])


@router.get("/{alliance_id}/")
async def get_alliance(
    alliance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("alliance.view")),
):
    result = await db.execute(select(Alliance).where(Alliance.alliance_id == alliance_id))
    alliance = result.scalar_one_or_none()
    if alliance is None:
        raise HTTPException(status_code=404, detail="Alliance not found")

    corp_result = await db.execute(
        select(AllianceCorporation).where(AllianceCorporation.alliance_id == alliance.id)
    )
    corps = corp_result.scalars().all()

    return {
        "alliance_id": alliance.alliance_id,
        "name": alliance.name,
        "ticker": alliance.ticker,
        "creator_corp_id": alliance.creator_corp_id,
        "executor_corp_id": alliance.executor_corp_id,
        "updated_at": alliance.updated_at,
        "member_corporations": [c.corporation_id for c in corps],
    }
