from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fastapi import APIRouter


# ── RBAC / Sidebar / Widget helpers ──────────────────────────────────────────

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
    required_permission: str | None = None  # 若设置，仅拥有该权限的用户可见


@dataclass
class PluginContext:
    db_session_factory: Any = None
    esi_client: Any = None


# ── Character Extension ────────────────────────────────────────────────────────

@runtime_checkable
class CharacterExtensionProvider(Protocol):
    """角色页面扩展接口

    插件实现此接口并在 on_enable() 中注册到 extension_registry，
    即可在角色详情页显示自定义内容。

    注册方式：
        extension_registry.register("character.extension", self, self.name)
    """

    def get_character_extension(
        self, character_id: int, db: "AsyncSession"
    ) -> "CharacterExtension | None":
        """返回角色扩展数据，不适用则返回 None"""
        ...


@dataclass
class CharacterExtension:
    """角色页面插件扩展内容"""
    character_id: int  # 用于验证
    title: str  # 显示标题
    widget: Literal["markdown", "stats", "iframe"]
    content: Any  # 内容格式见下方
    order: int = 100  # 排序
    css_class: str = ""  # 自定义 CSS 类

    # content 格式：
    #   markdown: str (Markdown 文本)
    #   stats: list[dict{label: str, value: str|number}]
    #   iframe: dict{url: str, height: int}


# ── Character Submodule ───────────────────────────────────────────────────────

@dataclass
class CharacterSubmodule:
    """插件为角色模块声明的独立子页面。

    注册后前端会在 /character/:id/{slug} 注册路由，并在角色侧边栏显示菜单项。
    页面内容通过 iframe 渲染，URL 由 iframe_url_template 中的 {character_id} 占位符代入。

    Example:
        CharacterSubmodule(
            slug="pap",
            label="出勤记录",
            icon="◈",
            iframe_url_template="http://localhost:5174/character/{character_id}/pap",
            order=10,
        )
    """
    slug: str                   # URL 片段，全局唯一，不可与内置页面冲突
    label: str                  # 侧边栏显示名
    iframe_url_template: str    # 含 {character_id} 占位符的 iframe URL
    icon: str = ""              # 可选 emoji 图标
    order: int = 100            # 在角色菜单中的排列顺序
    required_permission: str | None = None  # 若设置，仅拥有该权限的用户可见


@runtime_checkable
class CharacterSubmoduleProvider(Protocol):
    """声明插件为角色模块提供子页面的协议接口。

    插件仅需实现 get_character_submodules()，子模块声明会在安装/启用时
    序列化进 meta_snapshot，前端从 /api/v1/plugins/ 读取，无需运行时调用。
    """

    def get_character_submodules(self) -> list[CharacterSubmodule]: ...


# ── UI Schema — schema-driven frontend (no JS bundle required) ────────────────
#
# Plugins declare their UI structure in Python. The host SPA fetches this
# schema at runtime and renders pages using generic built-in components.
# Plugin authors only need to write Python; no Vite/Vue knowledge required.

@dataclass
class UIColumn:
    """A column definition for UITable."""
    key: str
    label: str
    type: Literal['text', 'number', 'date', 'badge', 'link'] = 'text'
    sortable: bool = False
    # badge type: maps field value → CSS color, e.g. {"approved": "#6abf69"}
    badge_map: dict[str, str] | None = None


@dataclass
class UIAction:
    """A button that either calls an API endpoint or navigates to a route.

    For API actions  set endpoint + method (+ row_key for row-level actions).
    For navigation   set navigate_to (route name, e.g. "fleet-action-create").
    """
    label: str
    endpoint: str | None = None          # path under /api/v1/plugins/{name}/
    navigate_to: str | None = None       # Vue Router route name
    method: Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] = 'POST'
    variant: Literal['default', 'primary', 'danger'] = 'default'
    confirm: str | None = None           # confirmation dialog text before executing
    # Row-level: append row[row_key] to endpoint, e.g. endpoint="actions", row_key="id"
    # → POST /api/v1/plugins/{name}/actions/{row.id}
    row_key: str | None = None


@dataclass
class UIFilter:
    """A filter control rendered above a UITable."""
    key: str
    label: str
    type: Literal['text', 'select'] = 'text'
    options: list[dict] | None = None    # select options: [{"label": "…", "value": "…"}]


@dataclass
class UITable:
    """A data table section.

    endpoint must return either:
      - A list:  [{...}, ...]
      - Paginated: {"items": [...], "total": N}
    Filters and pagination are appended as query params automatically.
    """
    endpoint: str                                  # GET path under plugin prefix
    columns: list[UIColumn] = field(default_factory=list)
    page_actions: list[UIAction] = field(default_factory=list)   # top-right buttons
    row_actions: list[UIAction] = field(default_factory=list)    # per-row buttons
    filters: list[UIFilter] = field(default_factory=list)
    page_size: int = 20


@dataclass
class UIFormField:
    """A single input field in a UIForm."""
    key: str
    label: str
    type: Literal['text', 'number', 'textarea', 'select', 'checkbox'] = 'text'
    required: bool = False
    options: list[dict] | None = None    # select options: [{"label": "…", "value": "…"}]
    placeholder: str = ''
    # Dynamic select: GET endpoint path (relative to plugin prefix) that returns
    # [{"label": "…", "value": "…"}].  Takes precedence over `options` when set.
    options_endpoint: str | None = None


@dataclass
class UIForm:
    """A data-entry form section.

    On submit the form data is sent to endpoint via method.
    Plugin endpoint should return {"message": "..."} on success.
    """
    endpoint: str
    method: Literal['POST', 'PUT', 'PATCH'] = 'POST'
    fields: list[UIFormField] = field(default_factory=list)
    submit_label: str = '提交'
    # Route name to navigate to after successful submit (optional)
    on_success_navigate: str | None = None


@dataclass
class UISection:
    """A visual block on a page — either a table or a form."""
    type: Literal['table', 'form']
    title: str = ''
    table: UITable | None = None
    form: UIForm | None = None


@dataclass
class UIPage:
    """A routable page within a plugin.

    name  → appended to route name:  "{plugin-name}-{name}"
    path  → appended to route path:  "/plugins/{plugin-name}/{path}"
    """
    name: str
    path: str
    title: str
    sections: list[UISection] = field(default_factory=list)


@dataclass
class UISchema:
    """The complete UI declaration for a plugin.

    Return this from HelmPlugin.get_ui_schema() to give the plugin a frontend
    without writing any JavaScript.
    """
    pages: list[UIPage] = field(default_factory=list)


# ── HelmPlugin base class ─────────────────────────────────────────────────────

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

    def get_beat_schedule(self) -> dict:
        """声明插件的 Celery Beat 定时任务（可热加载）。

        返回结构与 Celery 原生 beat_schedule 一致，键为条目本地名（在插件内唯一）：

            return {
                "analyze-all": {
                    "task": "monitor.analyze_all",   # 必须是 get_tasks() 中已注册的任务名
                    "schedule": 300.0,               # 间隔秒数（float）
                    "options": {"queue": "default"}, # 可选，路由队列等
                },
            }

        条目会被命名空间化为 "{plugin_name}:{key}" 后注入运行中的 Beat 进程，
        无需重启。管理员可像内置定时任务一样在后台覆盖其执行间隔。
        """
        return {}

    def get_sidebar_items(self) -> list[SidebarItem]:
        return []

    def get_character_submodules(self) -> list[CharacterSubmodule]:
        return []

    # ── iframe-based frontend ─────────────────────────────────────────────────

    def get_static_dir(self) -> Path | None:
        """Return the path to the plugin's compiled frontend files.

        The directory must contain an index.html entry point.
        Helm serves these files at /plugin-ui/{plugin-name}/ and renders
        the plugin inside an iframe.

        Example:
            return Path(__file__).parent / "frontend" / "dist"
        """
        return None

    def get_frontend_dev_url(self) -> str | None:
        """Return a local dev-server URL used during development only.

        When app_env is "development" and this returns a non-None value,
        Helm points the plugin iframe at this URL instead of the static files.
        This allows hot-reload during plugin development without rebuilding.

        Example:
            return "http://localhost:5174"
        """
        return None

    # ── Schema-driven frontend (deprecated — kept for import compatibility) ────

    def get_ui_schema(self) -> UISchema | None:
        return None

    # ── Event hooks ───────────────────────────────────────────────────────────

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
