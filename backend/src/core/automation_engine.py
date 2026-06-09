import logging
import time
import json
from src.core.mqtt_client import ChikGuardMQTTClient

logger = logging.getLogger("chikguard.automation")


class AutomationEngine:
    """
    Motor de Automação Reativa (Fase 2).
    Recebe sinais da Inteligência Artificial (Visão/Áudio) e Sensores IoT,
    e decide quando ligar/desligar atuadores (exaustores, painéis evaporativos)
    via MQTT para salvar a vida das aves.
    """

    def __init__(self, mqtt_client: ChikGuardMQTTClient):
        self.mqtt = mqtt_client
        self._last_action_time = {}
        self.cooldown_seconds = 120  # Evita ligar/desligar exaustor a cada segundo

    def process_telemetry(self, camera_id: str, temp_c: float, humidity_pct: float):
        """Avalia telemetria básica (Temperatura/Umidade)"""
        if temp_c > 31.0:
            self._trigger_action(
                camera_id, "exhaust_fan", "on", reason=f"Temperatura critica ({temp_c}°C)"
            )
        elif temp_c < 25.0:
            self._trigger_action(
                camera_id, "exhaust_fan", "off", reason=f"Temperatura normalizada ({temp_c}°C)"
            )
            self._trigger_action(
                camera_id, "heater", "on", reason=f"Temperatura baixa detectada ({temp_c}°C)"
            )
        elif temp_c > 28.0:
            self._trigger_action(
                camera_id, "heater", "off", reason=f"Temperatura adequada alcançada ({temp_c}°C)"
            )

    def process_ai_vision_anomaly(self, camera_id: str, anomaly_type: str, severity: str):
        """
        Avalia anomalias visuais (YOLO).
        Ex: Se a IA detectar aves amontoadas (frio) ou aves nos cantos (calor/estresse térmico).
        """
        if anomaly_type == "thermal_crowding" and severity in ["high", "critical"]:
            logger.warning(f"[Automação] IA detectou AGLOMERAÇÃO TÉRMICA extrema em {camera_id}.")
            self._trigger_action(
                camera_id, "heater", "on", reason="Aves amontoadas (IA detectou frio extremo)"
            )

        elif anomaly_type == "heat_stress_panting" and severity in ["high", "critical"]:
            logger.warning(f"[Automação] IA detectou OFEGANTE/ESTRESSE TÉRMICO em {camera_id}.")
            self._trigger_action(
                camera_id, "exhaust_fan", "on", reason="Estresse térmico visual (IA detectou calor)"
            )
            self._trigger_action(
                camera_id, "water_pump", "on", reason="Aumentar nebulização evaporativa"
            )

    def process_ai_audio_anomaly(self, camera_id: str, cough_idx: float, stress_idx: float):
        """
        Avalia anomalias acústicas.
        Ex: Altos índices de tosse podem exigir renovação de ar (reduzir amônia).
        """
        if cough_idx > 70.0:
            logger.warning(
                f"[Automação] IA Acústica detectou TOSSE ALTA ({cough_idx}%) em {camera_id}."
            )
            self._trigger_action(
                camera_id,
                "exhaust_fan",
                "on",
                reason=f"Renovação de ar de emergência (Amônia/Tosse: {cough_idx}%)",
            )

    def _trigger_action(self, camera_id: str, device: str, state: str, reason: str):
        """Dispara a ação via MQTT respeitando o Cooldown para não danificar o equipamento físico."""
        action_key = f"{camera_id}_{device}_{state}"
        now = time.time()

        last_time = self._last_action_time.get(action_key, 0)
        if (now - last_time) < self.cooldown_seconds:
            # Em período de cooldown, ignora para proteger o motor/relé
            return

        logger.info(
            f"⚡ [Automação] AÇÃO DISPARADA: {device.upper()} -> {state.upper()} ({reason})"
        )

        payload = {"device": device, "state": state, "reason": reason, "timestamp": int(now)}
        self.mqtt.publish_actuator(camera_id, f"set_{device}", payload)
        self._last_action_time[action_key] = now
