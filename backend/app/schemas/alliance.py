from datetime import datetime

from pydantic import BaseModel


class AllianceResponse(BaseModel):
    id: int
    alliance_id: int
    name: str
    ticker: str
    creator_corp_id: int | None
    executor_corp_id: int | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class AllianceCorporationResponse(BaseModel):
    corporation_id: int

    model_config = {"from_attributes": True}
