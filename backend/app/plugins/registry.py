from app.plugins.base import HelmPlugin

HELM_SDK_VERSION = "1.0.0"


class PluginRegistry:
    """Runtime registry of loaded plugins."""

    def __init__(self):
        self._plugins: dict[str, HelmPlugin] = {}
        self._route_prefixes: dict[str, str] = {}  # plugin_name -> mounted route prefix

    def register(self, plugin: HelmPlugin, route_prefix: str = "") -> None:
        self._plugins[plugin.name] = plugin
        if route_prefix:
            self._route_prefixes[plugin.name] = route_prefix

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)
        self._route_prefixes.pop(name, None)

    def get(self, name: str) -> HelmPlugin | None:
        return self._plugins.get(name)

    def all(self) -> list[HelmPlugin]:
        return list(self._plugins.values())

    def is_loaded(self, name: str) -> bool:
        return name in self._plugins

    def get_route_prefix(self, name: str) -> str | None:
        return self._route_prefixes.get(name)


class ExtensionRegistry:
    """
    Inter-plugin extension point registry.

    Plugins that provide a capability (e.g. MCP plugin) define a Protocol type
    as the interface contract. Plugins that implement the capability call
    register() in on_enable() and unregister_plugin() in on_disable().

    manager.py calls unregister_plugin() automatically on disable/uninstall,
    so manual unregistration in on_disable is optional (calls are idempotent).
    """

    def __init__(self):
        self._points: dict[str, list] = {}  # point_name -> [impl, ...]

    def register(self, point: str, impl: object, plugin_name: str) -> None:
        """Register an implementation for the named extension point."""
        impl._helm_plugin_name = plugin_name  # type: ignore[attr-defined]
        self._points.setdefault(point, []).append(impl)

    def unregister_plugin(self, plugin_name: str) -> None:
        """Remove all extension point implementations registered by this plugin."""
        for impls in self._points.values():
            impls[:] = [i for i in impls if getattr(i, "_helm_plugin_name", None) != plugin_name]

    def get_all(self, point: str) -> list:
        """Return all implementations registered under the given extension point name."""
        return list(self._points.get(point, []))

    def list_points(self) -> dict[str, list[str]]:
        """Return all registered extension points and their implementor plugin names."""
        return {
            point: [getattr(i, "_helm_plugin_name", "?") for i in impls]
            for point, impls in self._points.items()
            if impls
        }


registry = PluginRegistry()
extension_registry = ExtensionRegistry()
