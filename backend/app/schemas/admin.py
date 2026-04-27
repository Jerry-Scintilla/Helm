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
