import logging
import time

from src.core.mqtt_client import ChikGuardMQTTClient

logger = logging.getLogger("chikguard.automation")


class AutomationEngine:
    """
    Motor de Automação Reativa (Fase 2).
    Recebe sinais da Inteligência Artificial (Visão/Áudio) e Sensores IoT,
    e decide quando ligar/desligar atuadores (exaustores, painéis evaporativos)
    via MQTT para salvar a vida das aves.
    """

    def __init__(self, mqtt_client: ChikGuardMQTTClient, app_context_fn=None):
        self.mqtt = mqtt_client
        self._last_action_time = {}
        self.cooldown_seconds = 120  # Evita ligar/desligar exaustor a cada segundo
        self.app_context_fn = app_context_fn

    def process_telemetry(self, camera_id: str, temp_c: float, humidity_pct: float, ammonia_ppm: float = 0.0):
        """Avalia telemetria básica (Temperatura/Umidade/Amônia) usando regras do DB e fallback"""
        # Proteção contra Amônia (Gás Tóxico NH3) - Regra Zootécnica de Bem-Estar e Saúde Respiratória
        if ammonia_ppm > 20.0:
            self._trigger_action(
                camera_id, "exhaust_fan", "on", reason=f"Renovação de ar por amônia elevada ({ammonia_ppm:.1f} ppm > 20.0 ppm)"
            )
        # Regras Dinâmicas
        if self.app_context_fn:
            from database import AutomationRule

            with self.app_context_fn():
                rules = AutomationRule.query.filter_by(active=True).all()
                for rule in rules:
                    val = None
                    if rule.condition_variable == "temp_c":
                        val = temp_c
                    elif rule.condition_variable == "humidity_pct":
                        val = humidity_pct

                    if val is not None:
                        triggered = False
                        if rule.condition_operator == ">" and val > rule.condition_value:
                            triggered = True
                        elif rule.condition_operator == "<" and val < rule.condition_value:
                            triggered = True
                        elif rule.condition_operator == "==" and val == rule.condition_value:
                            triggered = True

                        if triggered:
                            self._trigger_action(
                                camera_id,
                                rule.action_device,
                                rule.action_state,
                                reason=f"Regra customizada: {rule.name} ({val} {rule.condition_operator} {rule.condition_value})",
                            )

        # Fallback de Automação Reativa Baseada em Comforto Térmico Zootécnico
        target_temp = 23.0
        if self.app_context_fn:
            from database import Batch
            from datetime import datetime
            from src.core.state_machine import get_ideal_temp_for_age
            with self.app_context_fn():
                try:
                    batch = Batch.query.filter_by(camera_id=camera_id, active=True).order_by(Batch.id.desc()).first()
                    if batch:
                        age_day = max(1, (datetime.utcnow().date() - batch.start_date.date()).days + 1)
                        target_temp = get_ideal_temp_for_age(age_day)
                except Exception as db_err:
                    logger.error(f"Erro ao consultar lote ativo para fallback de automacao: {db_err}")

        # Diferenciais dinâmicos adequados à idade/conforto das aves
        fan_on_temp = target_temp + 2.0
        heater_on_temp = target_temp - 0.5
        heater_off_temp = target_temp + 0.2

        # Regra de Somatória de Conforto Térmico (Índice de Estresse por Calor e Umidade combinados)
        # Prática consagrada na avicultura: Temp (°C) + UR (%) > 115 indica desconforto térmico severo.
        # Acima de 120, a saturação do ar impede a perda de calor respiratório.
        if (temp_c + humidity_pct) > 115.0 and temp_c > 24.0:
            self._trigger_action(
                camera_id, "exhaust_fan", "on",
                reason=f"Estresse termico combinado calor/umidade (Temp+UR = {temp_c + humidity_pct:.1f} > 115)"
            )

        if temp_c > fan_on_temp:
            self._trigger_action(
                camera_id, "exhaust_fan", "on", reason=f"Calor acima do conforto ({temp_c:.1f}°C > {fan_on_temp:.1f}°C)"
            )
        elif temp_c < heater_on_temp:
            self._trigger_action(
                camera_id, "exhaust_fan", "off", reason=f"Frio detectado. Ventilacao desligada ({temp_c:.1f}°C)"
            )
            self._trigger_action(
                camera_id, "heater", "on", reason=f"Aquecedor ativado preventivamente ({temp_c:.1f}°C < {heater_on_temp:.1f}°C)"
            )
        elif temp_c > heater_off_temp:
            self._trigger_action(
                camera_id, "heater", "off", reason=f"Temperatura de conforto reestabelecida. Aquecedor desligado ({temp_c:.1f}°C)"
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
            # SALVAGUARDA ZOOTÉCNICA CRÍTICA: Nunca ativar resfriamento evaporativo (nebulização)
            # se a umidade relativa já estiver muito alta (>= 80%), pois satura o ar e impede a perda
            # de calor latente das aves por respiração/panting, agravando a hipertermia e risco de morte.
            from src.core.state import sensor_state
            humidity = float(sensor_state.get("humidity_pct", 0.0))
            if humidity < 80.0:
                self._trigger_action(
                    camera_id, "water_pump", "on", reason=f"Ativar nebulização evaporativa (UR: {humidity:.1f}% < 80%)"
                )
            else:
                self._trigger_action(
                    camera_id, "water_pump", "off", reason=f"Bloqueio de nebulização evaporativa por alta umidade (UR: {humidity:.1f}% >= 80%)"
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
