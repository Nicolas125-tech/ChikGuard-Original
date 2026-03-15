import importlib.util
import os
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LoadedPlugin:
    plugin: Any
    path: str
    enabled: bool
    error: str | None = None


class PluginManager:
    def __init__(self, plugins_root: str, logger):
        self.plugins_root = plugins_root
        self.logger = logger
        self._plugins: List[LoadedPlugin] = []

    def load_all(self, context: Dict[str, Any]) -> None:
        self._plugins = []
        if not os.path.isdir(self.plugins_root):
            self.logger.info("Plugins directory not found: %s", self.plugins_root)
            return

        for entry in sorted(os.listdir(self.plugins_root)):
            plugin_file = os.path.join(self.plugins_root, entry, "plugin.py")
            if not os.path.isfile(plugin_file):
                continue
            self._plugins.append(self._load_single(plugin_file, context))

    def _load_single(self, plugin_file: str, context: Dict[str, Any]) -> LoadedPlugin:
        module_name = f"chikguard_plugin_{os.path.basename(os.path.dirname(plugin_file))}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                raise RuntimeError("invalid_spec")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "register"):
                raise RuntimeError("missing_register_function")
            plugin = module.register()
            plugin.on_startup(context)
            self.logger.info("Plugin loaded: %s", getattr(plugin.info, "name", module_name))
            return LoadedPlugin(plugin=plugin, path=plugin_file, enabled=True)
        except Exception as exc:
            self.logger.exception("Failed to load plugin at %s: %s", plugin_file, exc)
            return LoadedPlugin(plugin=None, path=plugin_file, enabled=False, error=str(exc))

    def emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        for item in self._plugins:
            if not item.enabled or item.plugin is None:
                continue
            try:
                item.plugin.on_event(event_type, payload)
            except Exception as exc:
                self.logger.exception("Plugin event error (%s): %s", item.path, exc)

    def list_plugins(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in self._plugins:
            if item.plugin is None:
                out.append(
                    {
                        "name": os.path.basename(os.path.dirname(item.path)),
                        "enabled": False,
                        "path": item.path,
                        "error": item.error,
                        "health": None,
                    }
                )
                continue
            info = getattr(item.plugin, "info", None)
            health = {}
            try:
                health = item.plugin.health()
            except Exception as exc:
                health = {"status": "error", "detail": str(exc)}
            out.append(
                {
                    "name": getattr(info, "name", os.path.basename(os.path.dirname(item.path))),
                    "version": getattr(info, "version", "unknown"),
                    "description": getattr(info, "description", ""),
                    "enabled": item.enabled,
                    "path": item.path,
                    "error": item.error,
                    "health": health,
                }
            )
        return out
