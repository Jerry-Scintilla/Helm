from datetime import datetime

from pydantic import BaseModel


class CharacterResponse(BaseModel):
    id: int
    character_id: int
    character_name: str
    corporation_id: int | None
    alliance_id: int | None
    is_active: bool
    scopes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletResponse(BaseModel):
    character_id: int
    balance: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class WalletJournalEntryResponse(BaseModel):
    id: int
    journal_id: int
    date: datetime | None
    ref_type: str
    first_party_id: int | None
    second_party_id: int | None
    amount: float | None
    balance: float | None
    description: str
    context_id: int | None
    context_id_type: str | None

    model_config = {"from_attributes": True}


class WalletTransactionResponse(BaseModel):
    id: int
    transaction_id: int
    date: datetime | None
    type_id: int
    location_id: int
    unit_price: float
    quantity: int
    client_id: int | None
    is_buy: bool
    is_personal: bool

    model_config = {"from_attributes": True}


class SkillResponse(BaseModel):
    skill_id: int
    trained_skill_level: int
    skillpoints_in_skill: int

    model_config = {"from_attributes": True}


class SkillQueueEntryResponse(BaseModel):
    queue_position: int
    skill_id: int
    finished_level: int
    start_date: datetime | None
    finish_date: datetime | None
    training_start_sp: int | None
    level_start_sp: int | None
    level_end_sp: int | None

    model_config = {"from_attributes": True}


class AssetResponse(BaseModel):
    item_id: int
    type_id: int
    location_id: int
    location_type: str
    quantity: int
    is_singleton: bool

    model_config = {"from_attributes": True}


class MailResponse(BaseModel):
    id: int
    mail_id: int
    subject: str
    from_id: int | None
    timestamp: datetime | None
    is_read: bool

    model_config = {"from_attributes": True}


class MailDetailResponse(MailResponse):
    body: str


class NotificationResponse(BaseModel):
    id: int
    notification_id: int
    type: str
    sender_id: int | None
    sender_type: str | None
    timestamp: datetime | None
    is_read: bool
    text: str

    model_config = {"from_attributes": True}
