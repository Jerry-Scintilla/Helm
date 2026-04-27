from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import APIRouter


@dataclass
class PermissionDef:
    name: str
    scope_type: str
    description: str = ""


@dataclass
class SidebarItem:
    label: str
    route: str
    icon: str = ""
    order: int = 100


@dataclass
class WidgetDef:
    component: str
    title: str
    order: int = 100


@dataclass
class PluginContext:
    db_session_factory: Any = None
    esi_client: Any = None


class HelmPlugin(ABC):
    """Base class for all Helm plugins."""

    name: str = ""
    version: str = "0.1.0"
    author: str = ""
    description: str = ""
    helm_sdk_version: str = ">=1.0,<2.0"

    # ── Backend extensions ────────────────────────────────────────────────────

    def get_router(self) -> "APIRouter | None":
        return None

    def get_models(self) -> list:
        return []

    def get_permissions(self) -> list[PermissionDef]:
        return []

    def get_esi_scopes(self) -> list[str]:
        return []

    def get_tasks(self) -> list:
        return []

    def get_sidebar_items(self) -> list[SidebarItem]:
        return []

    def get_dashboard_widgets(self) -> list[WidgetDef]:
        return []

    # ── Event hooks (Phase 3 will wire these up) ─────────────────────────────

    def on_character_updated(self, character_id: int, ctx: PluginContext) -> None:
        pass

    def on_corporation_updated(self, corporation_id: int, ctx: PluginContext) -> None:
        pass

    def on_killmail_received(self, killmail: dict, ctx: PluginContext) -> None:
        pass

    def on_notification_received(self, notification: dict, ctx: PluginContext) -> None:
        pass

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_install(self, ctx: PluginContext) -> None:
        pass

    def on_enable(self, ctx: PluginContext) -> None:
        pass

    def on_disable(self, ctx: PluginContext) -> None:
        pass

    def on_uninstall(self, ctx: PluginContext) -> None:
        pass
