from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class PluginInfo:
    name: str
    version: str
    description: str


class PluginBase:
    info = PluginInfo(name="plugin", version="0.0.0", description="Base plugin")

    def on_startup(self, context: Dict[str, Any]) -> None:
        """Called when the plugin is initialized. Override to provide custom startup logic."""

    def on_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Called when a core event is emitted. Override to handle events."""

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}
