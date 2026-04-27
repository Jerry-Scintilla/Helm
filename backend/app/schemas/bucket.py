from datetime import datetime

from pydantic import BaseModel


class BucketStateResponse(BaseModel):
    last_run_at: str | None = None
    token_count: int = 0
    active_task_count: int = 0
    health: str = "unknown"


class BucketResponse(BaseModel):
    id: int
    name: str
    capacity: int
    is_active: bool
    description: str
    created_at: datetime
    state: BucketStateResponse = BucketStateResponse()

    model_config = {"from_attributes": True}


class BucketCreateRequest(BaseModel):
    name: str
    capacity: int = 100
    description: str = ""


class BucketUpdateRequest(BaseModel):
    name: str | None = None
    capacity: int | None = None
    is_active: bool | None = None
    description: str | None = None
