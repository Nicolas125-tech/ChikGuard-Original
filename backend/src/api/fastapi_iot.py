from fastapi import APIRouter, Depends
from src.core.state import sensor_state
from src.security.fastapi_auth import get_current_user
import time

router = APIRouter(prefix="/api/iot", tags=["iot"])

# Estado global injetado pelo mqtt_bridge
iot_bridge_state = {
    "mqtt_connected": False,
    "broker_address": "",
    "topic": "",
    "last_message_at": None,
    "messages_received": 0
}

@router.get("/status")
def get_iot_status(user=Depends(get_current_user)):
    return {
        "mqtt_connected": iot_bridge_state["mqtt_connected"],
        "broker": iot_bridge_state["broker_address"],
        "topic": iot_bridge_state["topic"],
        "last_message_at": iot_bridge_state["last_message_at"],
        "messages_received": iot_bridge_state["messages_received"],
        "current_sensor_source": sensor_state.get("source", "init"),
        "uptime_sec": time.time() - sensor_state.get("updated_at", time.time()) if sensor_state.get("updated_at") else 0
    }
