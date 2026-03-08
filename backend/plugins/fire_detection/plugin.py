from src.plugins.base import PluginBase, PluginInfo


class FireDetectionPlugin(PluginBase):
    info = PluginInfo(
        name="fire_detection",
        version="0.1.0",
        description="Stub plugin for fire/smoke detector hook.",
    )

    def __init__(self):
        self._last_event_type = None

    def on_event(self, event_type, payload):
        self._last_event_type = event_type

    def health(self):
        return {"status": "ok", "last_event_type": self._last_event_type}


def register():
    return FireDetectionPlugin()
