from datetime import datetime

from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: int
    name: str
    scope: str
    description: str

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str
    permissions: list[PermissionResponse] = []

    model_config = {"from_attributes": True}


class RoleCreateRequest(BaseModel):
    name: str
    description: str = ""


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    roles: list[RoleResponse] = []

    model_config = {"from_attributes": True}


class AssignRoleRequest(BaseModel):
    role_id: int


class AssignPermissionRequest(BaseModel):
    permission_id: int


class SystemStatsResponse(BaseModel):
    total_users: int
    total_characters: int
    total_corporations: int
    total_alliances: int
    total_buckets: int
    total_bucket_tokens: int


class SDEImportRequest(BaseModel):
    url: str | None = None


class SDEImportResponse(BaseModel):
    task_id: str
    status: str
    source: str  # "url" | "upload"


class SDEImportStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class SDEStatusResponse(BaseModel):
    status: str  # idle | running | success | failed
    version: str | None = None
    release_date: str | None = None
    row_count: int | None = None
    last_import_at: str | None = None
    last_error: str | None = None
    source_url: str | None = None


class SDEUploadResponse(BaseModel):
    task_id: str
    status: str
    filename: str
