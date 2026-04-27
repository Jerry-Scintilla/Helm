from datetime import datetime

from pydantic import BaseModel


class CorporationResponse(BaseModel):
    id: int
    corporation_id: int
    name: str
    ticker: str
    member_count: int
    ceo_id: int | None
    alliance_id: int | None
    description: str
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class CorporationMemberResponse(BaseModel):
    character_id: int
    ship_type_id: int | None
    ship_type_name: str | None
    start_date: datetime | None
    logon_date: datetime | None
    logoff_date: datetime | None
    location_id: int | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class CorporationWalletResponse(BaseModel):
    wallet_division: int
    balance: float
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class CorporationWalletJournalResponse(BaseModel):
    id: int
    division: int
    journal_id: int
    date: datetime | None
    ref_type: str
    first_party_id: int | None
    second_party_id: int | None
    amount: float | None
    balance: float | None
    description: str

    model_config = {"from_attributes": True}


class CorporationAssetResponse(BaseModel):
    item_id: int
    type_id: int
    location_id: int
    location_type: str
    quantity: int
    is_singleton: bool
    updated_at: datetime | None

    model_config = {"from_attributes": True}
