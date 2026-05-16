from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.sde import SDEType
from app.models.user import User
from app.services.market import get_configured_region_id, get_market_prices
from app.services.sde import resolve_type_names

router = APIRouter(prefix="/api/v1/market", tags=["market"])

_MAX_TYPE_IDS = 50


@router.get("/prices")
async def market_prices(
    type_ids: str = Query(..., description="逗号分隔的 type_id 列表，最多 50 个"),
    region_id: int | None = Query(None, description="星域 ID，不传则使用管理员配置的默认区域"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_permission("character.view")),
):
    ids = [s.strip() for s in type_ids.split(",") if s.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="type_ids 不能为空")
    if len(ids) > _MAX_TYPE_IDS:
        raise HTTPException(status_code=400, detail=f"type_ids 最多 {_MAX_TYPE_IDS} 个")

    try:
        parsed_ids = [int(i) for i in ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="type_ids 必须为整数")

    effective_region = region_id if region_id is not None else await get_configured_region_id()
    prices = await get_market_prices(parsed_ids, region_id=effective_region)
    name_map = await resolve_type_names(parsed_ids, db, locale="zh")

    return {
        "region_id": effective_region,
        "prices": {
            str(tid): {
                "type_id": p.type_id,
                "type_name": name_map.get(p.type_id),
                "best_buy": p.best_buy,
                "best_sell": p.best_sell,
            }
            for tid, p in prices.items()
        },
    }


@router.get("/random-item")
async def random_market_item(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_permission("character.view")),
):
    """随机返回一个有市场分类的已发布物品。"""
    result = await db.execute(
        select(SDEType.type_id, SDEType.name)
        .where(SDEType.published == True, SDEType.market_group_id.isnot(None))
        .order_by(func.random())
        .limit(1)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="SDE 数据为空，请先导入 SDE")

    name_dict: dict = row[1] or {}
    name = name_dict.get("zh") or name_dict.get("en") or str(row[0])
    return {"type_id": row[0], "type_name": name}
