from src.plugins.base import PluginBase, PluginInfo


class FaceRecognitionPlugin(PluginBase):
    info = PluginInfo(
        name="face_recognition",
        version="0.1.0",
        description="Stub plugin for face recognition pipeline integration.",
    )

    def __init__(self):
        self._events_seen = 0

    def on_event(self, event_type, payload):
        if event_type == "event_log":
            self._events_seen += 1

    def health(self):
        return {"status": "ok", "events_seen": self._events_seen}


def register():
    return FaceRecognitionPlugin()
