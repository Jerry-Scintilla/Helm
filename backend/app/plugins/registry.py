from app.plugins.base import HelmPlugin


class PluginRegistry:
    """Runtime registry of loaded plugins. Phase 3 will add hot-swap logic."""

    def __init__(self):
        self._plugins: dict[str, HelmPlugin] = {}

    def register(self, plugin: HelmPlugin) -> None:
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)

    def get(self, name: str) -> HelmPlugin | None:
        return self._plugins.get(name)

    def all(self) -> list[HelmPlugin]:
        return list(self._plugins.values())

    def is_loaded(self, name: str) -> bool:
        return name in self._plugins


registry = PluginRegistry()
