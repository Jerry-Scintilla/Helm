from datetime import datetime

from pydantic import BaseModel


class APITokenResponse(BaseModel):
    id: int
    name: str
    token_prefix: str
    scopes: str
    expires_at: datetime | None
    last_used_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APITokenCreateRequest(BaseModel):
    name: str
    scopes: str = ""
    expires_at: datetime | None = None


class APITokenCreatedResponse(APITokenResponse):
    token: str
