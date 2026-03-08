from src.plugins.base import PluginBase, PluginInfo


class WeaponDetectionPlugin(PluginBase):
    info = PluginInfo(
        name="weapon_detection",
        version="0.1.0",
        description="Stub plugin for weapon detection model hook.",
    )

    def __init__(self):
        self._high_priority_events = 0

    def on_event(self, event_type, payload):
        level = str((payload or {}).get("level", "")).lower()
        if level in {"high", "critical"}:
            self._high_priority_events += 1

    def health(self):
        return {"status": "ok", "high_priority_events": self._high_priority_events}


def register():
    return WeaponDetectionPlugin()
