from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.character import Character
from app.models.corporation import Corporation, CorporationAsset, CorporationMember, CorporationWallet, CorporationWalletJournal
from app.models.sde import SDEType
from app.models.user import User
from app.services.esi_names import resolve_entity_names
from app.services.sde import enrich_type_icons, enrich_type_names_all_locales
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

    name_map = await resolve_entity_names([corp.ceo_id, corp.alliance_id])
    ceo_name = name_map.get(corp.ceo_id, {}).get("name") if corp.ceo_id else None
    alliance_name = name_map.get(corp.alliance_id, {}).get("name") if corp.alliance_id else None

    return {
        "corporation_id": corp.corporation_id,
        "name": corp.name,
        "ticker": corp.ticker,
        "member_count": corp.member_count,
        "ceo_id": corp.ceo_id,
        "ceo_name": ceo_name,
        "alliance_id": corp.alliance_id,
        "alliance_name": alliance_name,
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
    q: str | None = Query(None, description="按资产名称或地点 ID 搜索（模糊匹配）"),
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

    base = select(CorporationAsset).where(CorporationAsset.corporation_id == corp.id)

    # 按资产名称（全语言）或地点 ID 过滤 —— 全部下推到 SQL，避免一次性加载整张资产表。
    if q:
        q_term = q.strip()
        # Resolve type_ids whose name (any locale) matches, so name search runs
        # in the DB instead of enriching every row. SDEType.name is JSONB; casting
        # to text lets a single ILIKE cover all locales.
        matching_type_ids = (await db.execute(
            select(SDEType.type_id).where(
                func.lower(cast(SDEType.name, String)).like(f"%{q_term.lower()}%")
            )
        )).scalars().all()
        filters = [cast(CorporationAsset.location_id, String).like(f"%{q_term}%")]
        if matching_type_ids:
            filters.append(CorporationAsset.type_id.in_(matching_type_ids))
        base = base.where(or_(*filters))

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar_one()

    rows = (await db.execute(
        base.order_by(CorporationAsset.location_id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )).scalars().all()
    items = [
        {
            "item_id": a.item_id,
            "type_id": a.type_id,
            "location_id": a.location_id,
            "location_type": a.location_type,
            "quantity": a.quantity,
            "is_singleton": a.is_singleton,
        }
        for a in rows
    ]
    # Enrich only the current page.
    await enrich_type_names_all_locales(items, id_field="type_id", name_field="type_name", db=db)
    await enrich_type_icons(items, id_field="type_id", icon_field="icon_url", db=db)
    return {"total": total, "page": page, "per_page": per_page, "items": items}
