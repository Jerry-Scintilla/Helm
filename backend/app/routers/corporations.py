from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.character import Character
from app.models.corporation import Corporation, CorporationAsset, CorporationMember, CorporationWallet, CorporationWalletJournal
from app.models.user import User
from app.tasks.utils import DIRECTOR_SCOPE

router = APIRouter(prefix="/api/v1/corporations", tags=["corporations"])


async def _get_director_corp_ids(user_id: int, db: AsyncSession) -> set[int]:
    """Return EVE corporation IDs for which this user has a director character."""
    result = await db.execute(
        select(Character).where(
            Character.user_id == user_id,
            Character.is_active == True,
        )
    )
    characters = result.scalars().all()
    return {c.corporation_id for c in characters if c.corporation_id and DIRECTOR_SCOPE in c.scopes.split()}


@router.get("/")
async def list_corporations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("corporation.view")),
):
    corp_ids = await _get_director_corp_ids(current_user.id, db)
    if not corp_ids:
        return []
    result = await db.execute(
        select(Corporation).where(Corporation.corporation_id.in_(corp_ids))
    )
    corps = result.scalars().all()
    return [
        {
            "corporation_id": c.corporation_id,
            "name": c.name,
            "ticker": c.ticker,
            "member_count": c.member_count,
            "alliance_id": c.alliance_id,
            "updated_at": c.updated_at,
        }
        for c in corps
    ]


@router.get("/{corporation_id}/")
async def get_corporation(
    corporation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("corporation.view")),
):
    corp_ids = await _get_director_corp_ids(current_user.id, db)
    if corporation_id not in corp_ids:
        raise HTTPException(status_code=403, detail="No director access to this corporation")

    result = await db.execute(select(Corporation).where(Corporation.corporation_id == corporation_id))
    corp = result.scalar_one_or_none()
    if corp is None:
        raise HTTPException(status_code=404, detail="Corporation not found")

    return {
        "corporation_id": corp.corporation_id,
        "name": corp.name,
        "ticker": corp.ticker,
        "member_count": corp.member_count,
        "ceo_id": corp.ceo_id,
        "alliance_id": corp.alliance_id,
        "description": corp.description,
        "updated_at": corp.updated_at,
    }


@router.get("/{corporation_id}/members")
async def get_corporation_members(
    corporation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("corporation.view")),
):
    corp_ids = await _get_director_corp_ids(current_user.id, db)
    if corporation_id not in corp_ids:
        raise HTTPException(status_code=403, detail="No director access to this corporation")

    result = await db.execute(select(Corporation).where(Corporation.corporation_id == corporation_id))
    corp = result.scalar_one_or_none()
    if corp is None:
        raise HTTPException(status_code=404, detail="Corporation not found")

    member_result = await db.execute(
        select(CorporationMember)
        .where(CorporationMember.corporation_id == corp.id)
        .order_by(CorporationMember.logon_date.desc())
    )
    members = member_result.scalars().all()
    return [
        {
            "character_id": m.character_id,
            "ship_type_id": m.ship_type_id,
            "ship_type_name": m.ship_type_name,
            "start_date": m.start_date,
            "logon_date": m.logon_date,
            "logoff_date": m.logoff_date,
            "location_id": m.location_id,
        }
        for m in members
    ]


@router.get("/{corporation_id}/wallet")
async def get_corporation_wallet(
    corporation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("corporation.view")),
):
    corp_ids = await _get_director_corp_ids(current_user.id, db)
    if corporation_id not in corp_ids:
        raise HTTPException(status_code=403, detail="No director access to this corporation")

    result = await db.execute(select(Corporation).where(Corporation.corporation_id == corporation_id))
    corp = result.scalar_one_or_none()
    if corp is None:
        raise HTTPException(status_code=404, detail="Corporation not found")

    wallet_result = await db.execute(
        select(CorporationWallet)
        .where(CorporationWallet.corporation_id == corp.id)
        .order_by(CorporationWallet.wallet_division)
    )
    wallets = wallet_result.scalars().all()
    return [{"wallet_division": w.wallet_division, "balance": w.balance, "updated_at": w.updated_at} for w in wallets]


@router.get("/{corporation_id}/wallet/{division}/journal")
async def get_corporation_wallet_journal(
    corporation_id: int,
    division: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("corporation.view")),
):
    corp_ids = await _get_director_corp_ids(current_user.id, db)
    if corporation_id not in corp_ids:
        raise HTTPException(status_code=403, detail="No director access to this corporation")

    result = await db.execute(select(Corporation).where(Corporation.corporation_id == corporation_id))
    corp = result.scalar_one_or_none()
    if corp is None:
        raise HTTPException(status_code=404, detail="Corporation not found")

    journal_result = await db.execute(
        select(CorporationWalletJournal)
        .where(
            CorporationWalletJournal.corporation_id == corp.id,
            CorporationWalletJournal.division == division,
        )
        .order_by(CorporationWalletJournal.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = journal_result.scalars().all()
    return [
        {
            "journal_id": e.journal_id,
            "date": e.date,
            "ref_type": e.ref_type,
            "first_party_id": e.first_party_id,
            "second_party_id": e.second_party_id,
            "amount": e.amount,
            "balance": e.balance,
            "description": e.description,
        }
        for e in entries
    ]


@router.get("/{corporation_id}/assets")
async def get_corporation_assets(
    corporation_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("corporation.view")),
):
    corp_ids = await _get_director_corp_ids(current_user.id, db)
    if corporation_id not in corp_ids:
        raise HTTPException(status_code=403, detail="No director access to this corporation")

    result = await db.execute(select(Corporation).where(Corporation.corporation_id == corporation_id))
    corp = result.scalar_one_or_none()
    if corp is None:
        raise HTTPException(status_code=404, detail="Corporation not found")

    asset_result = await db.execute(
        select(CorporationAsset)
        .where(CorporationAsset.corporation_id == corp.id)
        .order_by(CorporationAsset.location_id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    assets = asset_result.scalars().all()
    return [
        {
            "item_id": a.item_id,
            "type_id": a.type_id,
            "location_id": a.location_id,
            "location_type": a.location_type,
            "quantity": a.quantity,
            "is_singleton": a.is_singleton,
        }
        for a in assets
    ]
