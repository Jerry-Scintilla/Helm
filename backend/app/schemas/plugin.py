from datetime import datetime

from pydantic import BaseModel


class PluginInfo(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    package_name: str
    entry_point: str
    version: str
    author: str
    description: str
    helm_sdk_version: str
    is_enabled: bool
    status: str
    error_message: str | None
    meta: dict
    frontend_url: str | None = None
    installed_at: datetime
    updated_at: datetime


class InstallRequest(BaseModel):
    package_name: str


class InstallResponse(BaseModel):
    task_id: str
    status: str


class PluginStatusResponse(BaseModel):
    name: str
    status: str
    is_enabled: bool
    is_loaded: bool
    router_mounted: bool
    error_message: str | None
