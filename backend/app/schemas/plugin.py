from datetime import datetime
from typing import Literal

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
    source: Literal["pypi", "testpypi"] = "pypi"
    # Exact version to install (e.g. "0.1.1"). None / "" installs the latest.
    version: str | None = None


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


class MarketplacePlugin(BaseModel):
    package_name: str
    display_name: str
    description: str
    author: str
    version: str | None
    tags: list[str]
    verified: bool
    homepage: str | None
    installed: bool
    # Version currently installed locally (None when not installed).
    installed_version: str | None = None
    # True when installed and the marketplace offers a strictly newer version.
    update_available: bool = False
    source: Literal["pypi", "testpypi"] = "pypi"


class MarketplaceRefreshResponse(BaseModel):
    count: int


class PluginVersionInfo(BaseModel):
    version: str
    released_at: str | None = None
    yanked: bool = False
    yanked_reason: str | None = None


class PluginVersionsResponse(BaseModel):
    package_name: str
    source: str
    versions: list[PluginVersionInfo]
