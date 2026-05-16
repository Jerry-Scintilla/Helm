from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.permissions import require_permission
from app.models.user import User
from app.services.market import get_configured_region_id, set_configured_region_id

router = APIRouter(prefix="/api/v1/admin/market", tags=["admin"])


class MarketConfigUpdate(BaseModel):
    region_id: int


@router.get("/config")
async def get_market_config(
    _current_user: User = Depends(require_permission("admin")),
):
    region_id = await get_configured_region_id()
    return {"region_id": region_id}


@router.put("/config")
async def update_market_config(
    body: MarketConfigUpdate,
    _current_user: User = Depends(require_permission("admin")),
):
    await set_configured_region_id(body.region_id)
    return {"region_id": body.region_id}
